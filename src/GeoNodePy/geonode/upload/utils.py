import os.path
from geonode.maps.models import Layer
from geoserver.catalog import FailedRequestError

from django.conf import settings

import os
import re
from zipfile import ZipFile
import logging

class UploadException(Exception):
    '''A handled exception meant to be presented to the user'''

    @staticmethod
    def from_exc(msg, ex):
        args = [msg]
        args.extend(ex.args)
        return UploadException(*args)


def rename_and_prepare(base_file):
    """ensure the file(s) have a proper name @hack this should be done
    in a nicer way, but needs fixing now To fix longer term: if
    geonode computes a name, the uploader should respect it As it
    is/was, geonode will compute a name based on the zipfile but the
    importer will use names as it unpacks the zipfile. Renaming all
    the various pieces seems a burden on the client
    
    Additionally, if a SLD file is present, extract this.
    """
    name, ext = os.path.splitext(os.path.basename(base_file))
    xml_unsafe = re.compile(r"(^[^a-zA-Z\._]+)|([^a-zA-Z\._0-9]+)")
    dirname = os.path.dirname(base_file)
    if ext.lower() == ".zip":
        zf = ZipFile(base_file, 'r')
        rename = False
        main_file = None
        for f in zf.namelist():
            name, ext = os.path.splitext(os.path.basename(f))
            if xml_unsafe.search(name):
                rename = True
            # @todo other files - need to unify extension handling somewhere
            if ext.lower() == '.shp':
                main_file = f
            elif ext.lower() == '.tif':
                main_file = f
            elif ext.lower() == '.csv':
                main_file = f
                
            # if an sld is there, extract so it can be found
            if ext.lower() == '.sld':
                zf.extract(f, dirname)
        if not main_file: raise UploadException(
                'Could not locate a shapefile or tif file')
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
            os.rename(os.path.join(dirname, f), os.path.join(dirname, safe))

    return os.path.join(
        dirname,
        xml_unsafe.sub('_', os.path.basename(base_file))
    )
        

def create_geoserver_db_featurestore():
    cat = Layer.objects.gs_catalog
    # get or create datastore
    try:
        ds = cat.get_store(settings.DB_DATASTORE_NAME)
    except FailedRequestError:
        logging.info(
            'Creating target datastore %s' % settings.DB_DATASTORE_NAME)
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