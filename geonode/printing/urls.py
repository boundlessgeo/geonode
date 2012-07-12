from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('geonode.printing.views',
    url(r'^template/(?P<templateid>\d+)$', 'template_view', name='template_view'),
)
