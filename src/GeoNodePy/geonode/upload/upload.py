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
from geonode.maps.gs_helpers import get_sld_for
from geonode.maps.utils import get_valid_layer_name
from geonode.maps.models import Layer
from geonode.maps.models import Contact
from geonode.maps.models import GeoNodeException
from geonode.maps.utils import get_default_user
from geonode.upload.models import Upload
from geonode.upload import signals
from geonode.upload.utils import create_geoserver_db_featurestore
from geonode.upload.utils import UploadException

import geoserver
from geoserver.resource import Coverage
from geoserver.resource import FeatureType
from gsuploader.uploader import BadRequest

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Max

import shutil
import json
import os.path
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class UploaderSession(object):
    """All objects held must be able to surive a good pickling"""

    # the gsuploader session object
    import_session = None

    # if provided, this file will be uploaded to geoserver and set as
    # the default
    import_sld_file = None

    # location of any temporary uploaded files
    tempdir = None

    #the main uploaded file, zip, shp, tif, etc.
    base_file = None

    #the name to try to give the layer
    name = None

    # blob of permissions JSON
    permissions = None

    # store most recently configured time transforms to support deleting
    time_transforms = None

    # defaults to REPLACE if not provided. Accepts APPEND, too
    update_mode = None

    # the title given to the layer
    layer_title = None

    # the abstract
    layer_abstract = None

    # computed target (dict since gsconfig objects do not pickle, but
    # attributes matching a datastore) of the import
    import_target = None

    # track the most recently completed upload step
    completed_step = None
    
    # the upload type - see the _pages dict in views
    upload_type = None

    def set_target(self, target):
        self.import_target = {
            'name': target.name,
            'workspace_name': target.workspace.name,
            'resource_type': target.resource_type
        }

    def __init__(self, **kw):
        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise Exception('not handled : %s' % k)

    def cleanup(self):
        """do what we should at the given state of the upload"""
        pass


def upload(name, base_file,
           user=None, time_attribute=None,
           time_transform_type=None,
           end_time_attribute=None, end_time_transform_type=None,
           presentation_strategy=None, precision_value=None,
           precision_step=None, use_big_date=False,
           overwrite=False):

    if user is None:
        user = get_default_user()
    if isinstance(user, basestring):
        user = User.objects.get(username=user)

    import_session = save_step(user, name, base_file, overwrite)

    upload_session = UploaderSession(
        base_file=base_file,
        name=name,
        import_session=import_session,
        layer_abstract="",
        layer_title=name,
        permissions=None
    )

    time_step(upload_session,
        time_attribute, time_transform_type,
        presentation_strategy, precision_value, precision_step,
        end_time_attribute=end_time_attribute,
        end_time_transform_type=end_time_transform_type,
        time_format=None, srs=None, use_big_date=use_big_date)

    target = run_import(upload_session, async=False)
    upload_session.set_target(target)
    final_step(upload_session, user)


def _log(msg, *args):
    logger.info(msg, *args)


def save_step(user, layer, spatial_files, overwrite=True):

    _log('Uploading layer: [%s], files [%s]', layer, spatial_files)

    
    if len(spatial_files) > 1:
        # we only support more than one file if they're rasters for mosaicing
        if not all([ f.file_type.layer_type == 'coverage' for f in spatial_files]):
            raise UploadException("Please upload only one type of file at a time")

    name = get_valid_layer_name(layer, overwrite)
    _log('Name for layer: [%s]', name)

    if not spatial_files:
        raise UploadException("Unable to recognize the uploaded file(s)")

    the_layer_type = spatial_files[0].file_type.layer_type

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

            # If our resource is already configured in the store it
            # needs to have the right resource type

            for resource in resources:
                if resource.name == name:

                    assert overwrite, "Name already in use and overwrite is False"

                    existing_type = resource.resource_type
                    if existing_type != the_layer_type:
                        msg =  ('Type of uploaded file %s (%s) does not match type '
                            'of existing resource type %s' % (name, the_layer_type, existing_type))
                        _log(msg)
                        raise GeoNodeException(msg)

    if the_layer_type not in (FeatureType.resource_type, Coverage.resource_type):
        raise Exception('Expected the layer type to be a FeatureType or Coverage, not %s' % the_layer_type)
    _log('Uploading %s', the_layer_type)

    error_msg = None
    try:
        # importer tracks ids by autoincrement but is prone to corruption
        # which potentially may reset the id - hopefully prevent this...
        next_id = Upload.objects.all().aggregate(Max('import_id')).values()[0]
        next_id = next_id + 1 if next_id else 1

        # save record of this whether valid or not - will help w/ debugging
        upload = Upload.objects.create(user=user, state=Upload.STATE_INVALID,
                                       upload_dir=spatial_files.dirname)

        # @todo settings for use_url or auto detection if geoserver is
        # on same host
        import_session = Layer.objects.gs_uploader.upload_files(
            spatial_files.all_files(), use_url=False, import_id=next_id, mosaic=len(spatial_files) > 1)

        upload.import_id = import_session.id
        upload.save()

        # any unrecognized tasks/files must be deleted or we can't proceed
        import_session.delete_unrecognized_tasks()

        if not import_session.tasks:
            error_msg = 'No valid upload files could be found'
        elif not import_session.tasks[0].items:
            error_msg = 'There may be a problem with the data provided'

        if len(import_session.tasks) > 1:
            error_msg = "Only a single upload is supported at the moment"

        if not error_msg and import_session.tasks:
            task = import_session.tasks[0]
            # single file tasks will have just a file entry
            if hasattr(task.source, 'files'):
                if not all([hasattr(f,'timestamp') for f in task.source.files]):
                    error_msg = ("Not all timestamps could be recognized."
                                 "Please ensure your files contain the correct formats.")

        if error_msg:
            upload.state = upload.STATE_INVALID
            upload.save()
           
        # @todo once the random tmp9723481758915 type of name is not
        # around, need to track the name computed above, for now, the
        # target store name can be used
    except Exception, e:
        logger.exception('Error creating import session')
        raise e

    if error_msg:
        raise UploadException(error_msg)
    else:
        _log("Finished upload of [%s] to GeoServer without errors.", name)

    return import_session


def run_import(upload_session, async):
    """Run the import, possibly asynchronously.

    Returns the target datastore.
    """
    import_session = upload_session.import_session
    import_session = Layer.objects.gs_uploader.get_session(import_session.id)
    if import_session.state == 'INCOMPLETE':
        item = upload_session.import_session.tasks[0].items[0]
        if item.state == 'NO_CRS':
            err = 'No projection found'
        else:
            err = item.state or 'Session not ready for import.'
        if err:
            raise Exception(err)

    # if a target datastore is configured, ensure the datastore exists
    # in geoserver and set the uploader target appropriately
    if (settings.DB_DATASTORE and
        import_session.tasks[0].items[0].layer.layer_type != 'RASTER'):
        target = create_geoserver_db_featurestore()
        _log('setting target datastore %s %s',
             target.name, target.workspace.name
            )
        import_session.tasks[0].set_target(
            target.name, target.workspace.name)
    else:
        target = import_session.tasks[0].target

    if upload_session.update_mode:
        _log('setting updateMode to %s', upload_session.update_mode)
        import_session.tasks[0].set_update_mode(upload_session.update_mode)

    _log('running import session')
    # run async if using a database
    import_session.commit(async)

    # @todo check status of import session - it may fail, but due to protocol,
    # this will not be reported during the commit
    return target


def time_step(upload_session, time_attribute, time_transform_type,
              presentation_strategy, precision_value, precision_step,
              end_time_attribute=None,
              end_time_transform_type=None,
              end_time_format=None,
              time_format=None,
              use_big_date=None):
    '''
    time_attribute - name of attribute to use as time

    time_transform_type - name of transform. either
    DateFormatTransform or IntegerFieldToDateTransform

    time_format - optional string format
    end_time_attribute - optional name of attribute to use as end time

    end_time_transform_type - optional name of transform. either
    DateFormatTransform or IntegerFieldToDateTransform

    end_time_format - optional string format
    presentation_strategy - LIST, DISCRETE_INTERVAL, CONTINUOUS_INTERVAL
    precision_value - number
    precision_step - year, month, day, week, etc.
    '''
    resource = upload_session.import_session.tasks[0].items[0].resource
    transforms = []

    def build_time_transform(att, type, format):
        trans = {'type': type, 'field': att}
        if format: trans['format'] = format
        return trans

    def build_att_remap_transform(att):
        # @todo the target is so ugly it should be obvious
        return {'type': 'AttributeRemapTransform',
                'field': att,
                'target': 'org.geotools.data.postgis.PostGISDialect$XDate'}
    if use_big_date is None:
        try:
            use_big_date = settings.USE_BIG_DATE
        except:
            use_big_date = False
    if time_attribute:
        if time_transform_type:

            transforms.append(
                build_time_transform(
                    time_attribute,
                    time_transform_type, time_format
                    )
                )

        if end_time_attribute and end_time_transform_type:

            transforms.append(
                build_time_transform(
                    end_time_attribute,
                    end_time_transform_type, end_time_format
                    )
                )

        # this must go after the remapping transform to ensure the
        # type change is applied

        if use_big_date:
            transforms.append(build_att_remap_transform(time_attribute))
            if end_time_attribute:

                transforms.append(
                    build_att_remap_transform(end_time_attribute)
                    )

        transforms.append({
            'type': 'CreateIndexTransform',
            'field': time_attribute
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


    if upload_session.time_transforms:
        upload_session.import_session.tasks[0].items[0].remove_transforms(
            upload_session.time_transforms
        )

    if transforms:
        logger.info('Setting transforms %s' % transforms)
        upload_session.import_session.tasks[0].items[0].add_transforms(transforms)
        try:
            upload_session.import_session.tasks[0].items[0].save()
            upload_session.time_transforms = transforms
        except BadRequest, br:
            raise UploadException.from_exc('Error configuring time:',br)


def csv_step(upload_session, lat_field, lng_field):
    import_session = upload_session.import_session
    item = import_session.tasks[0].items[0]
    feature_type = item.resource
    transform = {'type': 'AttributesToPointGeometryTransform',
                 'latField': lat_field,
                 'lngField': lng_field,
                 }
    feature_type.set_srs('EPSG:4326')
    item.remove_transforms(['AttributesToPointGeometryTransform'], by_type=True)
    item.add_transforms([transform])
    item.save()


def srs_step(upload_session, srs):
    resource = upload_session.import_session.tasks[0].items[0].resource
    srs = srs.strip().upper()
    print srs
    if not srs.startswith("EPSG:"):
        srs = "EPSG:%s" % srs
    logger.info('Setting SRS to %s', srs)
    resource.set_srs(srs)


def final_step(upload_session, user):
    import_session = upload_session.import_session
    _log('Reloading session %s to check validity', import_session.id)
    import_session = import_session.reload()
    upload_session.import_session = import_session

    # the importer chooses an available featuretype name late in the game need
    # to verify the resource.name otherwise things will fail.  This happens
    # when the same data is uploaded a second time and the default name is
    # chosen

    cat = Layer.objects.gs_catalog
    cat._cache.clear()

    # Create the style and assign it to the created resource
    # FIXME: Put this in gsconfig.py

    # @todo see above in save_step, regarding computed unique name
    name = import_session.tasks[0].items[0].layer.name

    _log('Getting from catalog [%s]', name)
    publishing = None
    for i in xrange(60):
        publishing = cat.get_layer(name)
        if publishing: break
        time.sleep(.5)

    if publishing is None:
        raise Exception("Expected to find layer named '%s' in geoserver, tried %s times" % (name, i))
    _log('Had to try %s times to get layer from catalog' % (i+1))

    _log('Creating style for [%s]', name)
    # get_files will not find the sld if it doesn't match the base name
    # so we've worked around that in the view - if provided, it will be here
    if upload_session.import_sld_file:
        _log('using provided sld file')
        base_file = upload_session.base_file
        sld_file = os.path.join(
            os.path.dirname(base_file), upload_session.import_sld_file
            )

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
            # what are we doing with this var?
            # style = cat.get_style(name)
            logger.warn(msg)
            e.args = (msg,)

        #FIXME: Should we use the fully qualified typename?
        publishing.default_style = cat.get_style(name)
        _log('default style set to %s', name)
        cat.save(publishing)

    _log('Creating Django record for [%s]', name)
    resource = import_session.tasks[0].items[0].resource
    target = import_session.tasks[0].target
    upload_session.set_target(target)
    typename = "%s:%s" % (target.workspace.name, resource.name)
    layer_uuid = str(uuid.uuid1())

    title = upload_session.layer_title
    abstract = upload_session.layer_abstract

    # @todo hacking - any cached layers might cause problems (maybe
    # delete hook on layer should fix this?)

    cat._cache.clear()

    defaults = dict(
            store=target.name,
            storeType=target.resource_type,
            typename=typename,
            workspace=target.workspace.name,
            title=title,# or resource.title,
            uuid=layer_uuid,
            abstract=abstract or '',
            owner=user,
            )
    _log('record defaults: %s', defaults)
    saved_layer, created = Layer.objects.get_or_create(
        name=resource.name,
        defaults=defaults
        )

    # Should we throw a clearer error here?
    assert saved_layer is not None

    # @todo if layer was not created, need to ensure upload target is
    # same as existing target

    _log('layer was created : %s', created)

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
        saved_layer = Layer.objects.get(name=name)
    except Layer.DoesNotExist, e:
        msg = ('There was a problem saving the layer %s to GeoNetwork/Django. Error is: %s' % (name, str(e)))
        logger.exception(msg)
        logger.debug('Attempting to clean up after failed save for layer [%s]', name)
        # Since the layer creation was not successful, we need to clean up
        # @todo implement/test cleanup
        # cleanup(name, layer_uuid)
        raise GeoNodeException(msg)

    # Verify it is correctly linked to GeoServer and GeoNetwork
    logger.info('Verifying layer in geoserver [%s]', (i+1))
    try:
        saved_layer.verify()
    except GeoNodeException, e:
        msg = ('The layer [%s] was not correctly saved to GeoNetwork/GeoServer. Error is: %s' % (name, str(e)))
        logger.exception(msg)
        saved_layer.delete()
        raise

    if upload_session.tempdir and os.path.exists(upload_session.tempdir):
        shutil.rmtree(upload_session.tempdir)

    upload = Upload.objects.get(import_id=import_session.id)
    upload.layer = saved_layer
    upload.save()

    signals.upload_complete.send(sender=final_step, layer=saved_layer)

    return saved_layer
