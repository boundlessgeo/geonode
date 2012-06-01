from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db.models import F
from django.template import defaultfilters
from django.contrib.gis.gdal import Envelope

from geonode.maps.models import *
from geonode.maps.views import _metadata_search
from geonode.maps.views import _split_query

# @hack - fix dependency by allowing injection
from mapstory.models import Topic
from mapstory.models import ContactDetail
from mapstory.models import get_view_cnts
from mapstory.models import get_ratings

from geonode.simplesearch.models import LayerIndex
from geonode.simplesearch.models import MapIndex
from geonode.simplesearch.models import filter_by_period

# and another
from avatar.util import get_default_avatar_url

import re
import operator
from datetime import date
from datetime import timedelta

_date_fmt = lambda dt: dt.strftime('%b %d %Y')

_exclude_patterns = []
_exclude_regex = []
'''Settings API - allow regular expressions to filter our layer name results'''
if hasattr(settings,'SIMPLE_SEARCH_EXCLUSIONS'):
    _exclude_patterns = settings.SIMPLE_SEARCH_EXCLUSIONS
    _exclude_regex = [ re.compile(e) for e in _exclude_patterns ]
    
def _filter_results(l):
    '''If the layer name doesn't match any of the patterns, it shows in the results'''
    return not any(p.search(l['name']) for p in _exclude_regex)

class Normalizer:
    '''Base class to allow lazy normalization of Map and Layer attributes.
    
    The fields we support sorting on are rank, title, last_modified.
    Instead of storing these (to keep pickle query size small), expose via methods.
    '''
    def __init__(self,o,data = None):
        self.o = o
        self.data = data
        self.dict = None
    def rank(self):
        return (self.rating + 1) * (self.views + 1)
    def title(self):
        return self.o.title
    def last_modified(self):
        abstract
    def as_dict(self):
        if self.dict is None:
            self.dict = self.populate(self.data or {})
            self.dict['iid'] = self.iid
            self.dict['rating'] = self.rating
            if hasattr(self,'views'):
                self.dict['views'] = self.views
        return self.dict
    
    
class MapNormalizer(Normalizer):
    def last_modified(self):
        return self.o.last_modified
    def populate(self, dict):
        map = self.o
        # resolve any local layers and their keywords
        # @todo this makes this search awful slow and these should be lazily evaluated
        local_kw = [ l.keywords.split(' ') for l in map.local_layers if l.keywords]
        keywords = local_kw and list(set( reduce(lambda a,b: a+b, local_kw))) or []
        return {
            'id' : map.id,
            'title' : map.title,
            'abstract' : defaultfilters.linebreaks(map.abstract),
            'topic' : '', # @todo
            'detail' : reverse('geonode.maps.views.map_controller', args=(map.id,)),
            'owner' : map.owner.username,
            'owner_detail' : reverse('about_storyteller', args=(map.owner.username,)),
            'last_modified' : _date_fmt(map.last_modified),
            '_type' : 'map',
            '_display_type' : 'MapStory',
            'thumb' : map.get_thumbnail_url(),
            'keywords' : keywords,
        }
        
class LayerNormalizer(Normalizer):
    def last_modified(self):
        return self.o.date
    def populate(self, doc):
        layer = self.o
        doc['owner'] = layer.owner.username
        doc['thumb'] = layer.get_thumbnail_url()
        doc['last_modified'] = _date_fmt(layer.date)
        doc['id'] = layer.id
        doc['_type'] = 'layer'
        doc['topic'] = layer.topic_category
        doc['abstract'] = defaultfilters.linebreaks(layer.abstract)
        doc['storeType'] = layer.storeType
        doc['_display_type'] = 'StoryLayer'
        if not settings.USE_GEONETWORK:
            doc['keywords'] = layer.keyword_list()
            doc['title'] = layer.title
            doc['detail'] = layer.get_absolute_url()

        owner = layer.owner
        if owner:
            doc['owner_detail'] = reverse('about_storyteller', args=(layer.owner.username,))
        return doc
    
def _annotate_results(normalizers):
    '''Generic content types are _much_ faster to deal with in bulk'''
    if not normalizers: return normalizers
    model = type(normalizers[0].o)
    cnts = get_view_cnts(model)
    ratings = get_ratings(model)
    for n in normalizers:
        n.views = cnts.get(n.o.id, 0)
        n.rating = float(ratings.get(n.o.id, 0))
    return normalizers
    
_default_avatar_url = get_default_avatar_url()
class OwnerNormalizer(Normalizer):
    def title(self):
        return self.o.user.username
    def last_modified(self):
        return self.o.user.date_joined
    def populate(self, doc):
        contact = self.o
        user = contact.user
        try:
            doc['thumb'] = user.avatar_set.all()[0].avatar_url(80)
        except IndexError:
            doc['thumb'] = _default_avatar_url
        doc['id'] = user.username
        doc['title'] = user.get_full_name() or user.username
        doc['organization'] = contact.organization
        doc['abstract'] = contact.blurb
        doc['last_modified'] = _date_fmt(self.last_modified())
        doc['detail'] = reverse('about_storyteller', args=(user.username,))
        doc['layer_cnt'] = Layer.objects.filter(owner = user).count()
        doc['map_cnt'] = Map.objects.filter(owner = user).count()
        doc['_type'] = 'owner'
        doc['_display_type'] = 'StoryTeller'
        return doc
    
def _get_owner_results(results, query, kw):
    # make sure all contacts have a user attached
    q = ContactDetail.objects.select_related().filter(user__isnull=False)
    
    if kw['bykw'] or kw['bysection']:
        # hard to handle - not supporting at the moment
        return
    
    byowner = kw.get('byowner')
    if byowner:
        q = q.filter(user__username__icontains = byowner)
    
    byextent = kw.get('byextent')
    if byextent:
        q = _filter_by_extent(MapIndex, q, byextent, True) | \
            _filter_by_extent(LayerIndex, q, byextent, True)
    
    byperiod = kw.get('byperiod')
    if byperiod:
        q = _filter_by_period(MapIndex, q, byperiod, True) | \
            _filter_by_period(LayerIndex, q, byperiod, True)
    
    byadded = parse_by_added(kw.get('byadded'))
    if byadded:
        q = q.filter(user__date_joined__gt = byadded)
    
    if query:
        q = q.filter(Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(blurb__icontains=query) |
            Q(organization__icontains=query) |
            Q(biography__icontains=query)
        )
    
    results.extend( _annotate_results(map(OwnerNormalizer,q)))
        
def _get_map_results(results, query, kw):
    q = Map.objects.filter(publish__status='Public')
    
    bysection = kw.get('bysection')
    if bysection:
        q = q.filter(topic__in=Topic.objects.filter(section__id=bysection))
        
    byowner = kw.get('byowner')
    if byowner:
        q = q.filter(owner__username=byowner)

    if query:
        q = q.filter(_build_kw_query(query))
        
    byextent = kw.get('byextent')
    if byextent:
        q = _filter_by_extent(MapIndex, q, byextent)
        
    byadded = parse_by_added(kw.get('byadded'))
    if byadded:
        q = q.filter(last_modified__gte=byadded)
    
    byperiod = kw.get('byperiod')
    if byperiod:
        q = _filter_by_period(MapIndex, q, byperiod)
        
    if not settings.USE_GEONETWORK:
        bykw = kw.get('bykw')
        if bykw:
            # this is a somewhat nested query but it performs way faster
            layers_with_kw = Layer.objects.filter(_build_kw_only_query(bykw)).values('typename')
            map_layers_with = MapLayer.objects.filter(name__in=layers_with_kw).values('map')
            q = q.filter(id__in=map_layers_with)
    
    results.extend( _annotate_results( map(MapNormalizer,q) ))
    
    
def _build_kw_query(query, query_keywords=False):
    '''Build an OR query on title and abstract from provided search text.
    if query_keywords is provided, include a query on the keywords attribute
    return a Q object
    '''
    kws = _split_query(query)
    subquery = [
        Q(title__icontains=kw) | Q(abstract__icontains=kw) for kw in kws
    ]
    if query_keywords:
        subquery = [ q | Q(keywords__icontains=kw) for q in subquery ]
    return reduce( operator.or_, subquery)

def _build_kw_only_query(query):
    return reduce(operator.or_, [Q(keywords__contains=kw) for kw in _split_query(query)])

def _filter_by_extent(index, q, byextent, user=False):
    env = Envelope(map(float,byextent.split(',')))
    extent_ids = index.objects.filter(extent__contained=env.wkt)
    if user:
        extent_ids = extent_ids.values('indexed__owner')
        return q.filter(user__in=extent_ids)
    else:
        extent_ids = extent_ids.values('indexed')
        return q.filter(id__in=extent_ids)
    
def _filter_by_period(index, q, byperiod, user=False):
    period_ids = filter_by_period(index, byperiod[0], byperiod[1])
    if user:
        period_ids = period_ids.values('indexed__owner')
        return q.filter(user__in=period_ids)
    else:
        period_ids = period_ids.values('indexed')
        return q.filter(id__in=period_ids)
    
def parse_by_added(spec):
    td = None
    if spec == 'today':
        td = timedelta(days=1)
    elif spec == 'week':
        td = timedelta(days=7)
    elif spec == 'month':
        td = timedelta(days=30)
    else:
        return None
    return date.today() - td
        
def _get_layer_results(results, query, kw):
    
    layer_results = None
    
    if settings.USE_GEONETWORK:
        # cache geonetwork results
        cache_key = query and 'search_results_%s' % query or 'search_results'
        layer_results = cache.get(cache_key)
        if not layer_results:
            layer_results = _metadata_search(query, 0, 1000)['rows']
            layer_results = filter(_filter_results, layer_results)
            # @todo search cache timeout in settings?
            cache.set(cache_key, layer_results, timeout=300)
        q = Layer.objects.filter(uuid__in=[ doc['uuid'] for doc in layer_results ])
    else:
        name_filter = reduce(operator.or_,[ Q(name__regex=f) for f in _exclude_patterns])
        q = Layer.objects.exclude(name_filter).filter(publish__status='Public')
        if query:
            q = q.filter(_build_kw_query(query,True)) | q.filter(name__icontains = query)
        # we can optimize kw search here
        # maps will still be slow, but this way all the layers are filtered
        # bybw before the cruddy in-memory filter
        bykw = kw.get('bykw')
        if bykw:
            q = q.filter(_build_kw_only_query(bykw))
            
    byowner = kw.get('byowner')
    if byowner:
        q = q.filter(owner__username=byowner)
            
    bysection = kw.get('bysection')
    if bysection:
        q = q.filter(topic__in=Topic.objects.filter(section__id=bysection))
    
    bytype = kw.get('bytype')
    if bytype and bytype != 'layer':
        q = q.filter(storeType = bytype)
        
    # @todo once supported via UI - this should be an OR with the section filter
    bytopic = kw.get('bytopic')
    if bytopic:
        q = q.filter(topic_category = bytopic)
        
    byextent = kw.get('byextent')
    if byextent:
        q = _filter_by_extent(LayerIndex, q, byextent)
        
    byadded = parse_by_added(kw.get('byadded'))
    if byadded:
        q = q.filter(date__gte=byadded)
        
    byperiod = kw.get('byperiod')
    if byperiod:
        q = _filter_by_period(LayerIndex, q, byperiod)
        
    # if we're using geonetwork, have to fetch the results from that
    if layer_results:
        normalizers = []
        layers = dict([ (l.uuid,l) for l in q])
    
        for doc in layer_results:
            layer = layers.get(doc['uuid'],None)
            if layer is None: continue #@todo - remote layer (how to get last_modified?)
            normalizers.append(LayerNormalizer(layer,doc))
    else:
        normalizers = map(LayerNormalizer, q)
    _annotate_results(normalizers)
    results.extend(normalizers)
                

def combined_search_results(query, kw):
    results = []
    
    bytype = kw.get('bytype', None)
    
    if bytype is None or bytype == u'map':
        _get_map_results(results, query, kw)
        
    if bytype is None or bytype == u'layer':
        _get_layer_results(results, query, kw)
        
    if bytype is None or bytype == u'owner':
        _get_owner_results(results, query, kw)
        
    return results