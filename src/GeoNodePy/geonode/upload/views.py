"""
Provide views for doing an upload.

The upload process may be multi step so views are all handled internally here
by the view function.

The pattern to support separation of view/logic is each step in the upload
process is suffixed with "_step". The view for that step is suffixed with
"_step_view". The goal of seperation of view/logic is to support various
programatic uses of this API. The logic steps should not accept request objects
or return response objects.

State is stored in a UploaderSession object stored in the user's session.
This needs to be made more stateful by adding a model.
"""
from geonode.maps.forms import NewLayerUploadForm
from geonode.maps.views import json_response
from geonode.upload import forms
from geonode.upload.models import Upload
from geonode.upload import upload
from geonode.upload import utils
from geonode.upload import files

from gsuploader import uploader

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import mail_admins
from django import db  
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.utils.html import escape
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.cache import cache_control
from django.contrib.auth.decorators import login_required

from httplib import BadStatusLine

import os
import logging
import re
import traceback
import uuid

logger = logging.getLogger(__name__)

_SESSION_KEY = 'geonode_upload_session'
_ALLOW_TIME_STEP = hasattr(settings, "UPLOADER_SHOW_TIME_STEP") and settings.UPLOADER_SHOW_TIME_STEP or False
_ASYNC_UPLOAD = settings.DB_DATASTORE == True

# at the moment, the various time support transformations require the database
if _ALLOW_TIME_STEP and not _ASYNC_UPLOAD:
    raise Exception("To support the time step, you must enable DB_DATASTORE")

_geoserver_down_error_msg = """
GeoServer is not responding. Please try again later and sorry for the incovenience.
"""

_unexpected_error_msg = """
An error occurred while trying to process your request.  Our administrator has
been notified, but if you'd like, please note this error code 
below and details on what you were doing when you encountered this error.  
That information can help us identify the cause of the problem and help us with 
fixing it.  Thank you!
"""


def _is_async_step(upload_session):
    return _ASYNC_UPLOAD and get_next_step(upload_session, offset=2) == 'run'


def _progress_redirect(step):
    return json_response(dict(
        success = True,
        redirect_to= reverse('data_upload', args=[step]),
        progress = reverse('data_upload_progress')
    ))


def unexpected_error(req, upload_session, e):
    code = uuid.uuid4()
    try:
        notify_error(req, upload_session, 'Unhandled Exception %s' % code)
    except:
        logger.exception('ERROR IN MAIL HANDLER!')
    errors= ['Sorry, but an error occurred:', _unexpected_error_msg, str(code)]
    return _error_response(req, exception=e, errors=errors)


def _error_response(req, exception=None, errors=None, force_ajax=False):
    if exception:
        logger.exception('Unexpected error in upload step')
    else:
        logger.warning('upload error: %s', errors)
    if req.is_ajax() or force_ajax:
        content_type = 'text/html' if not req.is_ajax() else None
        return json_response(exception=exception, errors=errors,
                             content_type=content_type)
    # is the only non-ajax response to a non-ajax ext form upload?
    if errors:
        exception = "<br>".join(errors)
    return HttpResponse(exception, status=400)


def _next_step_response(req, upload_session, force_ajax=False):
    # if the current step is the view POST for this step, advance one
    if req.method == 'POST':
        if upload_session.completed_step:
            advance_step(req, upload_session)
        else:
            upload_session.completed_step = 'save'

    next = get_next_step(upload_session)

    if next == 'time':
        # @TODO we skip time steps for coverages currently
        import_session = upload_session.import_session
        feature_type = import_session.tasks[0].items[0].resource
        if feature_type.resource_type == 'coverage':
            upload_session.completed_step = 'run'
            run_import(upload_session, async=False)
            return _next_step_response(req, upload_session)

    # @todo this is not handled cleanly - run is not a real step in that it
    # has no corresponding view served by the 'view' function.
    if next == 'run':
        upload_session.completed_step = next
        if _ASYNC_UPLOAD and req.is_ajax():
            return run_response(req, upload_session)
        else:
            # on sync we want to run the import and advance to the next step
            run_import(upload_session, async=False)
            return _next_step_response(req, upload_session,
                                       force_ajax=force_ajax)
    if req.is_ajax() or force_ajax:
        content_type = 'text/html' if not req.is_ajax() else None
        return json_response(redirect_to=reverse('data_upload', args=[next]),
                             content_type=content_type)
    return HttpResponseRedirect(reverse('data_upload', args=[next]))
    

def _create_time_form(import_session, form_data):
    feature_type = import_session.tasks[0].items[0].resource
    binding_names = {
        'Integer': 'Whole Number',
        'Long': 'Whole Number',
        'Double': 'Real Number',
        'String': 'Text',
        'Date': 'Date'
    }
    keys = [ att.binding.split('.')[-1] for att in feature_type.attributes ]
    atts = [ (att.name, binding_names[key]) for att, key in zip(feature_type.attributes, keys)
             if key in binding_names ]
    if form_data:
        return forms.TimeForm(form_data, attributes=atts)
    return forms.TimeForm(attributes=atts)


def save_step_view(req, session):
    if req.method == 'GET':
        s = os.statvfs('/')
        mb = s.f_bsize * s.f_bavail / (1024. * 1024)
        return render_to_response('upload/layer_upload.html',
            RequestContext(req, {
            'storage_remaining': "%d MB" % mb,
            'enough_storage': mb > 64,
            'async_upload' : _ASYNC_UPLOAD,
            'incomplete' : Upload.objects.get_incomplete_uploads(req.user)
        }))

    assert session is None
    form = NewLayerUploadForm(req.POST, req.FILES)
    tempdir = None
    if form.is_valid():
        tempdir, base_file = form.write_files()
        
        #@todo verify that scan_file does what we need
        name, ext = os.path.splitext(os.path.basename(base_file))
        found = files.scan_file(base_file)
        import_session = upload.save_step(req.user, name, found, overwrite=False)
        # @todo can we handle more than one?
        sld = None
        if found[0].sld_files:
            sld = found[0].sld_files[0]
        logger.info('provided sld is %s' % sld)
        upload_session = req.session[_SESSION_KEY] = upload.UploaderSession(
            tempdir=tempdir,
            base_file=base_file,
            name=name,
            import_session=import_session,
            layer_abstract=form.cleaned_data["abstract"],
            layer_title=form.cleaned_data["layer_title"],
            permissions=form.cleaned_data["permissions"],
            import_sld_file = sld,
            upload_type = found[0].file_type.code
        )
        return _next_step_response(req, upload_session, force_ajax=True)
    else:
        errors = []
        for e in form.errors.values():
            errors.extend([escape(v) for v in e])
        return _error_response(req, errors=errors)


def data_upload_progress(req):
    """This would not be needed if geoserver REST did not require admin role
    and is an inefficient way of getting this information"""
    upload_session = req.session[_SESSION_KEY]
    import_session = upload_session.import_session
    progress = import_session.tasks[0].items[0].get_progress()
    #another hacky part - set completed step back if error occurs
    if progress.get('state', None) == 'ERROR':
        # back up before the run step
        prerun = get_previous_step(upload_session, 'run')
        upload_session.completed_step = get_previous_step(upload_session, prerun)
        # and save session state back
        req.session[_SESSION_KEY] = upload_session
        Upload.objects.update_from_session(upload_session)
    return json_response(progress)


def srs_step_view(req, upload_session):
    import_session = upload_session.import_session

    form = None
    if req.method == 'POST':
        form = forms.SRSForm(req.POST)
        if form.is_valid():
            srs = form.cleaned_data['srs']
            upload.srs_step(upload_session, srs)
            return _next_step_response(req, upload_session)

    task = import_session.tasks[0]
    if task.state == 'INCOMPLETE':
        # CRS missing/unknown
        item = task.items[0]
        if item.state == 'NO_CRS':
            native_crs = item.resource.nativeCRS
            form = form or forms.SRSForm()

    if form:
        name = import_session.tasks[0].items[0].layer.name
        return render_to_response('upload/layer_upload_crs.html',
                                  RequestContext(req,{
                                        'native_crs' : native_crs,
                                        'form' : form,
                                        'layer_name' : name
                                  }))
    # mark this completed since there is no post-back when skipping
    upload_session.completed_step = 'srs'                              
    return _next_step_response(req, upload_session)


latitude_names = set(['latitude', 'lat'])
longitude_names = set(['longitude', 'lon', 'lng', 'long'])


def is_latitude(colname):
    return colname.lower() in latitude_names


def is_longitude(colname):
    return colname.lower() in longitude_names


def csv_step_view(request, upload_session):
    import_session = upload_session.import_session
    item = import_session.tasks[0].items[0]
    feature_type = item.resource
    attributes = feature_type.attributes

    # need to check if geometry is found
    # if so, can proceed directly to next step
    for attr in attributes:
        if attr.binding == u'com.vividsolutions.jts.geom.Point':
            upload_session.completed_step = 'csv'
            return _next_step_response(request, upload_session)

    # no geometry found, let's find all the numerical columns
    number_names = ['java.lang.Integer', 'java.lang.Double']
    point_candidates = [attr.name for attr in attributes
                        if attr.binding in number_names]
    point_candidates.sort()

    # form errors to display to user
    error = None

    lat_field = request.POST.get('lat', '')
    lng_field = request.POST.get('lng', '')

    if request.method == 'POST':
        if not lat_field or not lng_field:
            error = 'Please choose which columns contain the latitude and longitude data.'
        elif (lat_field not in point_candidates
              or lng_field not in point_candidates):
            error = 'Invalid latitude/longitude columns'
        elif lat_field == lng_field:
            error = 'You cannot select the same column for latitude and longitude data.'
        if not error:
            upload.csv_step(upload_session, lat_field, lng_field)
            return _next_step_response(request, upload_session)
    # try to guess the lat/lng fields from the candidates
    lat_candidate = None
    lng_candidate = None
    non_str_in_headers = False
    for candidate in attributes:
        if candidate.name in point_candidates:
            if not isinstance(candidate.name, basestring):
                non_str_in_headers = True
            elif is_latitude(candidate.name):
                lat_candidate = candidate.name
            elif is_longitude(candidate.name):
                lng_candidate = candidate.name
    if request.method == 'POST':
        guessed_lat_or_lng = False
        selected_lat = lat_field
        selected_lng = lng_field
    else:
        guessed_lat_or_lng = bool(lat_candidate or lng_candidate)
        selected_lat = lat_candidate
        selected_lng = lng_candidate
    present_choices = len(point_candidates) >= 2
    possible_data_problems = None
    if non_str_in_headers:
        possible_data_problems = "There are some suspicious column names in \
                                 your data. Did you provide column names in the header?"
    context = dict(present_choices=present_choices,
                   point_candidates=point_candidates,
                   async_upload=_is_async_step(upload_session),
                   selected_lat=selected_lat,
                   selected_lng=selected_lng,
                   guessed_lat_or_lng=guessed_lat_or_lng,
                   layer_name = import_session.tasks[0].items[0].layer.name,
                   error = error,
                   possible_data_problems = possible_data_problems
                   )
    return render_to_response('upload/layer_upload_csv.html',
                              RequestContext(request, context))


def time_step_view(request, upload_session):
    import_session = upload_session.import_session

    if request.method == 'GET':
        # check for invalid attribute names
        feature_type = import_session.tasks[0].items[0].resource
        if feature_type.resource_type == 'featureType':
            invalid = filter(lambda a: a.name.find(' ') >= 0, feature_type.attributes)
            if invalid:
                att_list = "<pre>%s</pre>" % '. '.join([a.name for a in invalid])
                msg = "Attributes with spaces are not supported : %s" % att_list
                return render_to_response('upload/upload_error.html', RequestContext(request,{
                    'error_msg' : msg
                }))
        context = {
            'time_form': _create_time_form(import_session, None),
            'layer_name': import_session.tasks[0].items[0].layer.name,
            'async_upload' : _is_async_step(upload_session)
        }
        return render_to_response('upload/layer_upload_time.html',
                                  RequestContext(request, context))
    elif request.method != 'POST':
        raise Exception()

    form = _create_time_form(import_session, request.POST)
    #@todo validation feedback, though we shouldn't get here
    if not form.is_valid():
        logger.warning('Invalid upload form: %s', form.errors)
        return _error_response(request, errors=["Invalid Submission"])

    cleaned = form.cleaned_data

    time_attribute_name, time_transform_type = None, None
    end_time_attribute_name, end_time_transform_type = None, None

    time_attribute = cleaned.get('attribute', None)
    end_time_attribute = cleaned.get('end_attribute', None)

    # submitted values will be in the form of '<name> [<type>]'
    name_pat = re.compile('^\S+')
    type_pat = re.compile('\[(.*)\]')

    if time_attribute:
        time_attribute_name = name_pat.search(time_attribute).group(0)
        time_attribute_type = type_pat.search(time_attribute).group(1)
        time_transform_type = None if time_attribute_type == 'Date' else 'DateFormatTransform'
    if end_time_attribute:
        end_time_attribute_name = name_pat.search(end_time_attribute).group(0)
        end_time_attribute_type = type_pat.search(end_time_attribute).group(1)
        end_time_transform_type = None if end_time_attribute_type == 'Date' else 'DateFormatTransform'

    if time_attribute:
        upload.time_step(
            upload_session,
            time_attribute=time_attribute_name,
            time_transform_type=time_transform_type,
            time_format=cleaned.get('attribute_format', None),
            end_time_attribute=end_time_attribute_name,
            end_time_transform_type=end_time_transform_type,
            end_time_format=cleaned.get('end_attribute_format', None),
            presentation_strategy=cleaned['presentation_strategy'],
            precision_value=cleaned['precision_value'],
            precision_step=cleaned['precision_step'],
        )

    return _next_step_response(request, upload_session)


def run_import(upload_session, async=_ASYNC_UPLOAD):
    # run_import can raise an exception which callers should handle
    target = upload.run_import(upload_session, async)
    upload_session.set_target(target)


def run_response(req, upload_session):
    run_import(upload_session)

    if _ASYNC_UPLOAD:
        next = get_next_step(upload_session)
        return _progress_redirect(next)
        
    return _next_step_response(req, upload_session)


def final_step_view(req, upload_session):
    saved_layer = upload.final_step(upload_session, req.user)
    return HttpResponseRedirect(saved_layer.get_absolute_url() + "?describe")


_steps = {
    'save': save_step_view,
    'time': time_step_view,
    'srs' : srs_step_view,
    'final': final_step_view,
    'csv': csv_step_view,
}

# note 'run' is not a "real" step, but handled as a special case
# and 'save' is the implied first step :P
_pages = {
    'shp' : ('srs', 'time', 'run', 'final'),
    'tif' : ('srs', 'time', 'run', 'final'),
    'jpg' : ('srs', 'time', 'run', 'final'),
    'png' : ('srs', 'time', 'run', 'final'),
    'csv' : ('csv', 'time', 'run', 'final'),
}

if not _ALLOW_TIME_STEP:
    for t, steps in _pages.items():
        steps = list(steps)
        if 'time' in steps:
            steps.remove('time')
        _pages[t] = tuple(steps)

def get_next_step(upload_session, offset = 1):
    assert upload_session.upload_type is not None
    try:
        pages = _pages[upload_session.upload_type]
    except KeyError, e:
        raise Exception('Unsupported file type: %s' % e.message)
    index = -1
    if upload_session.completed_step and upload_session.completed_step != 'save':
        index = pages.index(upload_session.completed_step)
    return pages[max(min(len(pages) - 1,index + offset),0)]


def get_previous_step(upload_session, post_to):
    pages = _pages[upload_session.upload_type]
    index = pages.index(post_to) - 1
    if index < 0: return 'save'
    return pages[index]


def advance_step(req, upload_session):
    upload_session.completed_step = get_next_step(upload_session)
    

def notify_error(req, upload_session, msg):
    # make sure the connection gets reset in case an earlier error broke it
    db.close_connection()

    upload_obj = None
    # grab the stacktrace now before another happens
    stack_trace = traceback.format_exc()
    if upload_session and upload_session.import_session and \
       upload_session.import_session.id:
        try:
            upload_obj = Upload.objects.get(import_id = upload_session.import_session.id)
        except Upload.DoesNotExist:
            pass
    post = ''.join([ '\n\t\t%s : "%s"' % kv for kv in req.POST.items() ])
    if req.FILES:
        for k in req.FILES:
            post = post + '\n\t\t(file) %s: "%s"' % (k, req.FILES[k])
    message = """
        Message: %(msg)s
        
        User: %(user)s
        
        Upload object id: %(id)s
        
        StackTrace: %(stack_trace)s

        POST: %(post)s
    """ % dict( msg=msg,
                user=req.user,
                id=upload_obj.id if upload_obj else None,
                stack_trace=''.join(stack_trace),
                post = post)
    mail_admins('upload error', message)


@login_required
@cache_control(no_cache=True, must_revalidate=True, private=True, max_age=0, no_store=True)
def view(req, step):
    """Main uploader view"""
    upload_session = None

    if step is None:
        if 'id' in req.GET:
            # upload recovery
            upload_obj = get_object_or_404(Upload, import_id=req.GET['id'], user=req.user)
            session = upload_obj.get_session()
            if session:
                req.session[_SESSION_KEY] = session
                next = get_next_step(session)
                return _steps[next](req, session)
        
        step = 'save'

        # delete existing session
        if _SESSION_KEY in req.session:
            del req.session[_SESSION_KEY]

    else:
        if not _SESSION_KEY in req.session:
            return render_to_response("upload/no_upload.html", RequestContext(req,{}))
        upload_session = req.session[_SESSION_KEY]

    try:
        if req.method == 'GET' and upload_session:
            # set the current step to match the requested page - this
            # could happen if the form is ajax w/ progress monitoring as
            # the advance would have already happened @hacky
            upload_session.completed_step = get_previous_step(upload_session, step)

        resp = _steps[step](req, upload_session)
        # must be put back to update object in session
        if upload_session:
            if step == 'final':
                # we're done with this session, wax it
                Upload.objects.update_from_session(upload_session)
                upload_session = None
                del req.session[_SESSION_KEY]
            else:
                req.session[_SESSION_KEY] = upload_session
        elif _SESSION_KEY in req.session:
            upload_session = req.session[_SESSION_KEY]
        if upload_session:
            Upload.objects.update_from_session(upload_session)
        return resp
    except BadStatusLine:
        logger.exception('bad status line, geoserver down?')
        return _error_response(req, errors=[_geoserver_down_error_msg])
    except uploader.RequestFailed, e:
        logger.exception('request failed')
        errors = e.args
        # http bad gateway or service unavailable
        if int(errors[0]) in (502,503):
            return _error_response(req, errors=[_geoserver_down_error_msg])
        return unexpected_error(req, upload_session, e)
    except utils.UploadException, e:
        logger.exception('upload exception')
        return _error_response(req, errors=e.args)
    except uploader.BadRequest, e:
        logger.exception('bad request')
        return _error_response(req, errors=e.args)
    except Exception, e:
        return unexpected_error(req, upload_session, e)


@login_required
def delete(req, id):
    upload = get_object_or_404(Upload, import_id=id)
    if req.user != upload.user:
        raise PermissionDenied()
    upload.delete()
    return HttpResponse('OK')
