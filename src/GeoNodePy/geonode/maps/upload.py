"""
Provide views and business logic of doing an upload.

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
from geonode.maps.utils import *
from geonode.maps.models import *
from geonode.maps.forms import NewLayerUploadForm
from geonode.maps.views import json_response
from geonode.maps.utils import get_default_user

from gsuploader.uploader import RequestFailed

from django import forms
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import escape
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext

import shutil
import json
import os.path
from zipfile import ZipFile



_SESSION_KEY = 'geonode_upload_session'

class UploaderSession(object):
    'All objects held must be able to surive a good pickling'
    
    import_session = None
    'the gsuploader session object'
    
    import_sld_file = None
    'if provided, this file will be uploaded to geoserver and set as the default'
    
    tempdir = None
    'location of any temporary uploaded files'
    
    base_file = None
    'the main uploaded file, zip, shp, tif, etc.'
    
    name = None
    'the name to try to give the layer'
    
    permissions = None
    'blob of permissions JSON'
    
    form = None #@todo - needed?
    
    update_mode = None
    'defaults to REPLACE if not provided. Accepts APPEND, too'
    
    layer_title = None
    'the title given to the layer'
    
    layer_abstract = None
    'the abstract'
    
    import_target = None
    'computed target (dict since gsconfig objects do not pickle, but attributes matching a datastore) of the import'
    
    _completed_step = None
    'track the most recently completed upload step'
    
    def set_target(self,target):
        self.import_target = {
            'name' : target.name,
            'workspace_name' : target.workspace.name,
            'resource_type' : target.resource_type
        }
    
    def __init__(self, **kw):
        for k,v in kw.items():
            if hasattr(self,k):
                setattr(self,k,v)
            else:
                raise Exception('not handled : %s' % k)
    def cleanup(self):
        """do what we should at the given state of the upload"""
        pass
    
def upload(name, base_file, user=None, time_attribute=None, time_transform_type=None,
    end_time_attribute=None, end_time_transform_type=None,
    presentation_strategy=None, precision_value=None, precision_step=None,
    use_big_date=False, overwrite = False):
        
    
    if user is None:
        user = get_default_user()
    if isinstance(user, basestring):
        user = User.objects.get(username = user)
        
    s = UploaderSession()
    s.target = 'foo'
    import_session = save_step(user, name, base_file, overwrite)
    upload_session = UploaderSession(
        base_file = base_file,
        name = name,
        import_session = import_session,
        layer_abstract = "",
        layer_title = name,
        permissions = None
    )
    time_step(upload_session,
        time_attribute, time_transform_type,
        presentation_strategy, precision_value, precision_step,
        end_time_attribute = end_time_attribute, 
        end_time_transform_type = end_time_transform_type,
        time_format = None, srs = None, use_big_date=use_big_date)
    target = run_import(upload_session, async=False)
    upload_session.set_target(target)
    final_step(upload_session, user)

def _log(msg, *args):
    logger.info(msg, *args)
    
def _redirect(step):
    return json_response(redirect_to=reverse('data_upload', args=[step]))

def _rename_and_prepare(base_file):
    """ensure the file(s) have a proper name
    @hack this should be done in a nicer way, but needs fixing now
    To fix longer term: if geonode computes a name, the uploader should respect it
    As it is/was, geonode will compute a name based on the zipfile but the importer
    will use names as it unpacks the zipfile. Renaming all the various pieces
    seems a burden on the client
    """
    name,ext = os.path.splitext( os.path.basename(base_file) )
    xml_unsafe = re.compile(r"(^[^a-zA-Z\._]+)|([^a-zA-Z\._0-9]+)")
    dirname = os.path.dirname(base_file)
    if ext == ".zip":
        zf = ZipFile(base_file,'r')
        rename = False
        main_file = None
        for f in zf.namelist():
            name, ext = os.path.splitext( os.path.basename(f) )
            if xml_unsafe.search(name):
                rename = True
            # @todo other files - need to unify extension handling somewhere
            if ext.lower() == '.shp':
                main_file = f
        if not main_file: raise Exception('Could not locate a shapefile')
        if rename:
            # dang, have to unpack and rename
            zf.extractall(dirname)
        zf.close()
        if rename:
            os.unlink(base_file)
            base_file = os.path.join(dirname, main_file)
            
    for f in os.listdir(dirname):
        safe = xml_unsafe.sub("_", f)
        if safe != f:
            os.rename( os.path.join(dirname,f), os.path.join(dirname, safe))
            
    return os.path.join(dirname,xml_unsafe.sub('_', os.path.basename(base_file)))

def save_step_view(req, session):
    assert session is None
    
    form = NewLayerUploadForm(req.POST, req.FILES)
    tempdir = None
    if form.is_valid():
        tempdir, base_file = form.write_files()
        base_file = _rename_and_prepare(base_file)
        name, __ = os.path.splitext(os.path.basename(base_file))
        import_session = save_step(req.user, name, base_file, overwrite=False) 
        req.session[_SESSION_KEY] = UploaderSession(
            tempdir = tempdir,
            base_file = base_file,
            name = name,
            import_session = import_session,
            layer_abstract = form.cleaned_data["abstract"],
            layer_title = form.cleaned_data["layer_title"],
            permissions = form.cleaned_data["permissions"]
        )
        return _redirect('time')
    else:
        errors = []
        for e in form.errors.values():
            errors.extend([escape(v) for v in e])
        return json_response(errors = errors)

def save_step(user, layer, base_file, overwrite = True):
    
    _log('Uploading layer: [%s], base file [%s]', layer, base_file)
    
    assert os.path.exists(base_file), 'invalid base_file - does not exist'

    name = get_valid_layer_name(layer, overwrite)
    _log('Name for layer: [%s]', name)

    # Step 2. Check that it is uploading to the same resource type as the existing resource
    the_layer_type = layer_type(base_file)
        
    # Check if the store exists in geoserver
    try:
        store = Layer.objects.gs_catalog.get_store(name)
    except geoserver.catalog.FailedRequestError, e:
        # There is no store, ergo the road is clear
        pass
    else:
        # If we get a store, we do the following:
        resources = store.get_resources()
        # Is it empty?
        if len(resources) == 0:
            # What should we do about that empty store?
            if overwrite:
                # We can just delete it and recreate it later.
                store.delete()
            else:
                msg = ('The layer exists and the overwrite parameter is %s' % overwrite)
                raise GeoNodeException(msg)
        else:
            # If our resource is already configured in the store it needs to have the right resource type
            for resource in resources:
                if resource.name == name:
                    assert overwrite, "Name already in use and overwrite is False"
                    existing_type = resource.resource_type
                    if existing_type != the_layer_type:
                        msg =  ('Type of uploaded file %s (%s) does not match type '
                            'of existing resource type %s' % (layer_name, the_layer_type, existing_type))
                        _log(msg)
                        raise GeoNodeException(msg)

    if the_layer_type not in  (FeatureType.resource_type, Coverage.resource_type):
        raise Exception('Expected the layer type to be a FeatureType or Coverage, not %s' % the_layer_type)
    _log('Uploading %s', the_layer_type)

    error_msg = None
    try:
        # @todo settings for use_url or auto detection if geoserver is on same host
        import_session = Layer.objects.gs_uploader.upload(base_file, use_url = False)
        if not import_session.tasks:
            error_msg = 'No upload tasks were created'
        elif not import_session.tasks[0].items:
            error_msg = 'No upload items found for task'
        else:
            # save record of this
            Upload.objects.create_from_session(user, import_session)
        # @todo once the random tmp9723481758915 type of name is not around, need to track the name
        # computed above, for now, the target store name can be used
    except Exception, e:
        logger.exception('Error creating import session')
        error_msg = str(e)
        
    if error_msg:
        raise Exception('Could not save the layer %s, there was an upload error: %s' % (name, error_msg))
    else:
        _log("Finished upload of [%s] to GeoServer without errors.", name)

    return import_session

    
class TimeForm(forms.Form):
    presentation_strategy = forms.CharField(required=False)
    srs = forms.CharField(required=False)
    precision_value = forms.IntegerField(required=False)
    precision_step = forms.ChoiceField(required=False,choices=[
        ('years',)*2,
        ('months',)*2,
        ('days',)*2,
        ('hours',)*2,
        ('minutes',)*2,
        ('seconds',)*2
    ])
    
    def __init__(self, *args, **kwargs):
        # have to remove these from kwargs or Form gets mad
        time_names = kwargs.pop('time_names',None)
        text_names = kwargs.pop('text_names',None)
        year_names = kwargs.pop('year_names',None)
        super(TimeForm, self).__init__(*args,**kwargs)
        self._build_choice('time_attribute',time_names)
        self._build_choice('end_time_attribute',time_names)
        self._build_choice('text_attribute',text_names)
        self._build_choice('end_text_attribute',text_names)
        if text_names:
            self.fields['text_attribute_format'] = forms.CharField(required=False)
            self.fields['end_text_attribute_format'] = forms.CharField(required=False)
        self._build_choice('year_attribute',year_names)
        self._build_choice('end_year_attribute',year_names)
            
    def _build_choice(self, att, names):
        if names:
            choices =  [ ("","<None>") ] + [ (a,a) for a in names ]
            self.fields[att] = forms.ChoiceField(choices=choices,required=False)
    # @todo implement clean
    
def _create_time_form(import_session, form_data):
    feature_type = import_session.tasks[0].items[0].resource
    filter_type = lambda b : [ att.name for att in feature_type.attributes if att.binding == b]
    args = dict(
        time_names = filter_type('java.util.Date'),
        text_names = filter_type('java.lang.String'),
        year_names = filter_type('java.lang.Integer') + filter_type('java.lang.Long') +
            filter_type('java.lang.Double')
    )
    if form_data:
        return TimeForm(form_data,**args)
    return TimeForm(**args)

def _create_db_featurestore():
    """Override the imported method from utils that does too much"""
    cat = Layer.objects.gs_catalog
    try:
        ds = cat.get_store(settings.DB_DATASTORE_NAME)
    except FailedRequestError, e:
        logging.info("Creating target datastore %s",settings.DB_DATASTORE_NAME)
        ds = cat.create_datastore(settings.DB_DATASTORE_NAME)
        ds.connection_parameters.update(
            host=settings.DB_DATASTORE_HOST,
            port=settings.DB_DATASTORE_PORT,
            database=settings.DB_DATASTORE_DATABASE,
            user=settings.DB_DATASTORE_USER,
            passwd=settings.DB_DATASTORE_PASSWORD,
            dbtype=settings.DB_DATASTORE_TYPE)
        cat.save(ds)
        ds = cat.get_store(settings.DB_DATASTORE_NAME)

    return ds

def _do_upload(upload_session):
    if upload_session.update_mode:
        try:
            run_import(request)
            return HttpResponse(json.dumps({
            "success": True,
            "redirect_to": layer.get_absolute_url() + "?describe"}))
        except Exception, ex:
            logging.exception("Unexpected error during upload.")
            return json_response(error = "Unexpected error during upload: " + escape(str(e)))
    else:
        # only feature types have attributes
        if hasattr(upload_session.import_session.tasks[0].items[0].resource,"attributes"):
            return json_response(reverse('data_upload',args=['time']))
        else:
            return HttpResponse("Can't handle this data",status=500)
             


def data_upload_progress(req, upload_session):
    """This would not be needed if geoserver REST did not require admin role
    and is an inefficient way of getting this information"""
    import_session = upload_session.import_session
    progress = import_session.tasks[0].items[0].get_progress()
    return HttpResponse(json.dumps(progress),"application/json")
    
def time_step_context(import_session, form_data):

    context =  {
        'time_form' : _create_time_form(import_session, form_data),
        'layer_name' : import_session.tasks[0].items[0].layer.name,
    }

    if settings.DB_DATASTORE:
        # we are importing to a database, use async
        context['progress_endpoint'] = reverse('data_upload',args=['progress'])

    # check for various recoverable incomplete states
    if import_session.tasks[0].state == 'INCOMPLETE':
        # CRS missing/unknown
        if import_session.tasks[0].items[0].state == 'NO_CRS':
            context['missing_crs'] = True
            # there should be a native_crs
            context['native_crs'] = import_session.tasks[0].items[0].resource.nativeCRS

    return context

def run_import(upload_session, async):
    """Run the import, possibly asynchronously.
    
    Returns the target datastore.
    """
    import_session = upload_session.import_session
    # if a target datastore is configured, ensure the datastore exists in geoserver
    # and set the uploader target appropriately
    if settings.DB_DATASTORE:
        target = _create_db_featurestore()
        _log('setting target datastore %s %s',target.name,target.workspace.name)
        import_session.tasks[0].set_target(target.name,target.workspace.name)
    else:
        target = import_session.tasks[0].target

    if upload_session.update_mode:
        _log('setting updateMode to %s',update_mode)
        import_session.tasks[0].set_update_mode(update_mode)

    _log('running import session')
    # run async if using a database
    import_session.commit(async)

    # @todo check status of import session - it may fail, but due to protocol,
    # this will not be reported during the commit
    return target

def time_step_view(request, upload_session):
    if request.method == 'GET':
        return render_to_response('maps/layer_upload_step2.html',
            RequestContext(request, time_step_context(upload_session.import_session, form_data=None))
        )
    elif request.method != 'POST':
        raise Exception()
        
    import_session = upload_session.import_session
        
    form = _create_time_form(import_session, request.POST)
    #@todo validation feedback
    if not form.is_valid():
        raise Exception("form invalid")
    
    cleaned = form.cleaned_data
    
    time_attribute, time_transform_type = None, None
    end_time_attribute, end_time_transform_type = None, None
    
    field_collectors = [
        ('time_attribute',None),
        ('text_attribute','DateFormatTransform'),
        ('year_attribute','IntegerFieldToDateTransform')
    ]
    
    for field, transform_type in field_collectors:
        time_attribute = cleaned.get( field, None)
        if time_attribute:
            time_transform_type = transform_type
            break
    for field, transform_type in field_collectors:
        end_time_attribute = cleaned.get( "end_" + field, None)
        if end_time_attribute:
            end_time_transform_type = transform_type
            break
            
    async = settings.DB_DATASTORE is not None
    try:
        time_step(
            upload_session,
            time_attribute = time_attribute,
            time_transform_type = time_transform_type,
            time_format = cleaned.get('text_attribute_format',None),
            end_time_attribute = end_time_attribute,
            end_time_transform_type = end_time_transform_type,
            end_time_format = cleaned.get('end_text_attribute_format',None),
            presentation_strategy = cleaned['presentation_strategy'],
            precision_value = cleaned['precision_value'],
            precision_step = cleaned['precision_step'],
            srs = cleaned.get('srs',None)
        )
        target = run_import(upload_session, async)
    except Exception, ex:
        return json_response(exception=ex);

    upload_session.set_target(target)
    
    if async:
        return json_response(redirect_to=reverse('data_upload',args=['final']))

    return HttpResponseRedirect(upload_session.layer.get_absolute_url() + "?describe")

    
def time_step(upload_session, time_attribute, time_transform_type, 
    presentation_strategy, precision_value, precision_step,
    end_time_attribute = None, end_time_transform_type = None, end_time_format = None,
    time_format = None, srs = None, use_big_date = None):
    '''
    Apply any time transformations, set dimension info, and SRS 
    (@todo SRS should be extracted to a different step)
    
    time_attribute - name of attribute to use as time
    time_transform_type - name of transform. either DateFormatTransform or IntegerFieldToDateTransform
    time_format - optional string format
    end_time_attribute - optional name of attribute to use as end time
    end_time_transform_type - optional name of transform. either DateFormatTransform or IntegerFieldToDateTransform
    end_time_format - optional string format
    presentation_strategy - LIST, DISCRETE_INTERVAL, CONTINUOUS_INTERVAL
    precision_value - number
    precision_step - year, month, day, week, etc.
    srs - optional srs to add to transformation
    '''
    resource = upload_session.import_session.tasks[0].items[0].resource
    transforms = []
    def build_time_transform(att, type, format):
        trans = {'type': type, 'field': att}
        if format: trans['format'] = format
        return trans
    def build_att_remap_transform(att):
        # @todo the target is so ugly it should be obvious
        return {'type' : 'AttributeRemapTransform', 'field' : att, 'target' : 'org.geotools.data.postgis.PostGISDialect$XDate'}
    if use_big_date is None:
        try:
            use_big_date = settings.USE_BIG_DATE
        except:
            use_big_date = False
    if time_attribute:
        if time_transform_type:
            transforms.append(build_time_transform(time_attribute, time_transform_type, time_format))
        if end_time_attribute and end_time_transform_type:
            transforms.append(build_time_transform(end_time_attribute, end_time_transform_type, end_time_format))
        # this must go after the remapping transform to ensure the type change is applied
        if use_big_date:
            transforms.append(build_att_remap_transform(time_attribute))
            if end_time_attribute:
                transforms.append(build_att_remap_transform(end_time_attribute))
        transforms.append({
            'type' : 'CreateIndexTransform',
            'field' : time_attribute
        })
        resource.add_time_dimension_info(
            time_attribute,
            end_time_attribute,
            presentation_strategy,
            precision_value,
            precision_step,
        )
        logger.info('Setting time dimension info')
        resource.save()
        
    if transforms:
        logger.info('Setting transforms %s',transforms)
        upload_session.import_session.tasks[0].items[0].set_transforms(transforms)
        upload_session.import_session.tasks[0].items[0].save()
        
    if srs:
        srs = srs.strip().upper()
        if not srs.startswith("EPSG:"):
            srs = "EPSG:%s" % srs
        logger.info('Setting SRS to %s',srs)
        # this particular REST operation provides nice error handling
        try:
            resource.set_srs(srs)
        except RequestFailed,ex:
            args = ex.args
            if ex.args[1] == 400:
                errors = json.loads(ex.args[2])
                args = "\n".join(errors['errors'])
            raise Exception(args)

def final_step_view(req, upload_session):
    saved_layer = final_step(upload_session, req.user)
    return HttpResponseRedirect(saved_layer.get_absolute_url() + "?describe")

def final_step(upload_session, user):
    target = upload_session.import_target
    import_session = upload_session.import_session
    
    _log('Reloading session %s to check validity',import_session.id)
    import_session = Layer.objects.gs_uploader.get_session(import_session.id)
    upload_session.import_session = import_session
    
    # @todo the importer chooses an available featuretype name late in the game
    # need to verify the resource.name otherwise things will fail.
    # This happens when the same data is uploaded a second time and the default
    # name is chosen
    
    cat = Layer.objects.gs_catalog

    # Create the style and assign it to the created resource
    # FIXME: Put this in gsconfig.py
    
    # @todo see above in save_step, regarding computed unique name
    name = import_session.tasks[0].items[0].layer.name
    
    _log('Creating style for [%s]', name)
    publishing = cat.get_layer(name)
    if publishing is None:
        raise Exception("Expected to find layer named ''%s' in geoserver",name)

    # get_files will not find the sld if it doesn't match the base name
    # so we've worked around that in the view - if provided, it will be here
    if upload_session.import_sld_file:
        _log('using provided sld file')
        base_file = upload_session.base_file
        sld_file = os.path.join(os.path.dirname(base_file), upload_session.import_sld_file)
        f = open(sld_file, 'r')
        sld = f.read()
        f.close()
    else:
        sld = get_sld_for(publishing)

    if sld is not None:
        try:
            cat.create_style(name, sld)
        except geoserver.catalog.ConflictingDataError, e:
            msg = 'There was already a style named %s in GeoServer, cannot overwrite: "%s"' % (name, str(e))
            style = cat.get_style(name)
            logger.warn(msg)
            e.args = (msg,)

        #FIXME: Should we use the fully qualified typename?
        publishing.default_style = cat.get_style(name)
        _log('default style set to %s', name)
        cat.save(publishing)
    

    _log('Creating Django record for [%s]', name)
    resource = import_session.tasks[0].items[0].resource
    typename = "%s:%s" % (target['workspace_name'], resource.name)
    layer_uuid = str(uuid.uuid1())
    
    title = upload_session.layer_title
    abstract = upload_session.layer_abstract
    
    # @todo hacking - any cached layers might cause problems (maybe delete hook on layer should fix this?)
    cat._cache.clear()
    saved_layer, created = Layer.objects.get_or_create(name=resource.name, defaults=dict(
        store=target['name'],
        storeType=target['resource_type'],
        typename=typename,
        workspace=target['workspace_name'],
        title=title or resource.title,
        uuid=layer_uuid,
        abstract=abstract or '',
        owner=user,
        )
    )
    
    assert saved_layer is not None
    
    # @todo if layer was not created, need to ensure upload target is same as existing target
    _log('layer was created : %s',created)

    if created:
        saved_layer.set_default_permissions()

    # Create the points of contact records for the layer
    # A user without a profile might be uploading this
    _log('Creating points of contact records for [%s]', name)
    poc_contact, __ = Contact.objects.get_or_create(user=user,
                                           defaults={"name": user.username })
    author_contact, __ = Contact.objects.get_or_create(user=user,
                                           defaults={"name": user.username })
    saved_layer.poc = poc_contact
    saved_layer.metadata_author = author_contact

    _log('Saving to geonetwork')
    saved_layer.save_to_geonetwork()

    # Set default permissions on the newly created layer
    # FIXME: Do this as part of the post_save hook
    
    permissions = upload_session.permissions
    _log('Setting default permissions for [%s]', name)
    if permissions is not None:
        from geonode.maps.views import set_layer_permissions
        set_layer_permissions(saved_layer, permissions)

    _log('Verifying the layer [%s] was created correctly' % name)

    # Verify the object was saved to the Django database
    # @revisit - this should always work since we just created it above and the
    # message is confusing
    try:
        Layer.objects.get(name=name)
    except Layer.DoesNotExist, e:
        msg = ('There was a problem saving the layer %s to GeoNetwork/Django. Error is: %s' % (layer, str(e)))
        logger.exception(msg)
        logger.debug('Attempting to clean up after failed save for layer [%s]', name)
        # Since the layer creation was not successful, we need to clean up
        # @todo implement/test cleanup
        # cleanup(name, layer_uuid)
        raise GeoNodeException(msg)

    # Verify it is correctly linked to GeoServer and GeoNetwork
    try:
        saved_layer.verify()
    except GeoNodeException, e:
        msg = ('The layer [%s] was not correctly saved to GeoNetwork/GeoServer. Error is: %s' % (name, str(e)))
        logger.exception(msg)
        e.args = (msg,)
        # Deleting the layer
        saved_layer.delete()
        raise
    
    if upload_session.tempdir and os.path.exists(upload_session.tempdir):
        shutil.rmtree(upload_session.tempdir)
    
    return saved_layer


_steps = {
    'save' : save_step_view,
    'progress' : data_upload_progress,
    'time' : time_step_view,
    'final' : final_step_view
}
    
def view(req, step):
    """Main uploader view"""
    
    upload_session = None
    
    if step is None:
        step = 'save'
        # @todo should warn user if session is being abandoned!
        if _SESSION_KEY in req.session:
            del req.session[_SESSION_KEY]
    else:
        assert _SESSION_KEY in req.session, 'Expected uploader session for step %s' % step
        upload_session = req.session[_SESSION_KEY]
        
    try:
        resp = _steps[step](req, upload_session)
        if upload_session:
            req.session[_SESSION_KEY] = upload_session
            Upload.objects.update_from_session(upload_session.import_session)
        return resp
    except Exception,e:
        if upload_session:
            upload_session.cleanup()
        return json_response('Error in upload step : %s',exception = e)
