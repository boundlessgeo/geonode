from geonode.maps.models import Layer
from geoserver.catalog import FailedRequestError

from django.conf import settings

import logging

class UploadException(Exception):
    '''A handled exception meant to be presented to the user'''

    @staticmethod
    def from_exc(msg, ex):
        args = [msg]
        args.extend(ex.args)
        return UploadException(*args)


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