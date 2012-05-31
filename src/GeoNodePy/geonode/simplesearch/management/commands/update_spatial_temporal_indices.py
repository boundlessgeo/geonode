from django.core.management.base import BaseCommand
from geonode.maps.models import Map
from geonode.maps.models import Layer
from geonode.simplesearch.models import index_object
import logging
from optparse import make_option
import traceback

class Command(BaseCommand):
    help = 'Update simplesearch indices'
    option_list = BaseCommand.option_list + (
        make_option('--update', dest="update", default=False, action="store_true",
            help="Update any existing entries"),
    )

    def handle(self, *args, **opts):
        logging.getLogger('geonode.simplesearch.models').setLevel(logging.DEBUG)
        update = opts['update']
        def index(o):
            try:
                index_object(o,update=update)
            except:
                print 'error indexing', o
                traceback.print_exc()
                
        map(index,Map.objects.all())
        map(index,Layer.objects.all())