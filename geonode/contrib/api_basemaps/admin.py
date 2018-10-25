# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2016 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from django.contrib import admin
from geonode.contrib.api_basemaps.models import MapBaseLayer
from django.contrib import messages


def enable_basemap(modeladmin, request, queryset):
    for instance in queryset:
        instance.enabled = True
        instance.save()

    messages.success(request,
                     '%d basemaps are now enabled.' % len(queryset))
enable_basemap.short_description = 'Enable selected Basemaps'

def disable_basemap(modeladmin, request, queryset):
    for instance in queryset:
        instance.enabled = False
        instance.save()

    messages.success(request,
                     '%d basemaps are now disabled.' % len(queryset))
disable_basemap.short_description = 'Disable selected Basemaps'


class MapBaseLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'visibility', 'enabled')
    actions = [enable_basemap, disable_basemap]

admin.site.register(MapBaseLayer, MapBaseLayerAdmin)
