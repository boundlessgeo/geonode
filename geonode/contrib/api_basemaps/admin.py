from django.contrib import admin
from geonode.contrib.api_basemaps.models import MapBaseLayer
from django.contrib import messages


def publish(modeladmin, request, queryset):
    for instance in queryset:
        instance.is_published = True
        instance.save()

    messages.success(request,
                     '%d basemaps are now published.' % len(queryset))
publish.short_description = 'Publish Selected Basemaps'

def unpublish(modeladmin, request, queryset):
    for instance in queryset:
        instance.is_published = False
        instance.save()

    messages.success(request,
                     '%d basemaps are now unpublished.' % len(queryset))
unpublish.short_description = 'Unpublish Selected Basemaps'


class MapBaseLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'visibility', 'is_published')
    actions = [publish, unpublish]

admin.site.register(MapBaseLayer, MapBaseLayerAdmin)
