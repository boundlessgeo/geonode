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
from django.contrib import messages

from geonode.base.admin import MediaTranslationAdmin, ResourceBaseAdminForm
from geonode.layers.models import Layer, Attribute, AttributeOption, Style, Constraint
from geonode.layers.models import LayerFile, UploadSession
from geonode.geoserver.helpers import set_styles, gs_catalog


class AttributeInline(admin.TabularInline):
    model = Attribute


class LayerAdminForm(ResourceBaseAdminForm):

    class Meta:
        model = Layer
        fields = '__all__'

        
class DefaultStyleListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'has default style'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'has_default_style'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar. In this case display a filter
        option for whethe a layer has a default style or not.
        """
        return (
            ('true', 'Yes'),
            ('false', 'No')
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        if self.value() == 'true':
            return queryset.filter(default_style__isnull=False)
        elif self.value() == 'false':
            return queryset.filter(default_style__isnull=True)


def sync_styles(modeladmin, request, queryset):
    count = 0
    for instance in queryset:
        try:
            if instance.storeType not in ['remoteStore']:
                set_styles(instance, gs_catalog)
                instance.save()
                count =+ 1
        except Exception as e:
            messages.error(request, '%s for %s' % (str(e), instance.name))
    messages.success(request,
                     'Styles for %d layers synchronized succcessfully.' % count)
sync_styles.short_description = 'Sync remote styles'


class LayerAdmin(MediaTranslationAdmin):
    list_display = (
        'id',
        'typename',
        'service_type',
        'title',
        'date',
        'category',
        'is_published',
        'featured')
    list_display_links = ('id',)
    list_editable = ('title', 'category','is_published','featured')
    list_filter = ('storeType', 'owner', 'category', 'is_published','featured',
                   'restriction_code_type__identifier', 'date', 'date_type',
                   DefaultStyleListFilter)
    search_fields = ('typename', 'title', 'abstract', 'purpose',)
    filter_horizontal = ('contacts',)
    date_hierarchy = 'date'
    readonly_fields = ('uuid', 'typename', 'workspace')
    inlines = [AttributeInline]
    form = LayerAdminForm
    actions = [sync_styles,]


class AttributeAdmin(admin.ModelAdmin):
    model = Attribute
    list_display_links = ('id',)
    list_display = (
        'id',
        'layer',
        'attribute',
        'description',
        'attribute_label',
        'attribute_type',
        'display_order')
    list_filter = ('layer', 'attribute_type')
    search_fields = ('attribute', 'attribute_label',)

class AttributeOptionAdmin(admin.ModelAdmin):
     model = AttributeOption
     list_display_links = ('id',)
     list_display = (
         'id',
         'layer',
         'attribute',
         'value',
         'label')
     list_filter = ('layer', 'attribute',)
     search_fields = ('value', 'label',)


class StyleAdmin(admin.ModelAdmin):
    model = Style
    list_display_links = ('sld_title',)
    list_display = ('id', 'name', 'sld_title', 'workspace', 'sld_url')
    list_filter = ('workspace',)
    search_fields = ('name', 'workspace',)


class LayerFileInline(admin.TabularInline):
    model = LayerFile


class UploadSessionAdmin(admin.ModelAdmin):
    model = UploadSession
    list_display = ('date', 'user', 'processed')
    inlines = [LayerFileInline]

class ConstraintAdmin(admin.ModelAdmin):
    model = Constraint
    list_display_links = ('attribute',)
    list_display = ('get_layer', 'attribute', 'control_type', 'initial_value', 'is_integer',)
    list_filter = ('attribute__layer',)

    def get_layer(self, obj):
        return obj.attribute.layer
    get_layer.short_description = 'Layer'
    get_layer.admin_order_field = 'attribute__layer'

admin.site.register(Layer, LayerAdmin)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(AttributeOption, AttributeOptionAdmin)
admin.site.register(Style, StyleAdmin)
admin.site.register(UploadSession, UploadSessionAdmin)
admin.site.register(Constraint, ConstraintAdmin)
