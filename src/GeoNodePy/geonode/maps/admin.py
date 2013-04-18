from geonode.maps.models import Map, Layer, MapLayer, Contact, ContactRole, Role
from django.contrib.contenttypes.models import ContentType
from django.contrib import admin
from django import forms
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse


class MapLayerInline(admin.TabularInline):
    model = MapLayer

class ContactRoleInline(admin.TabularInline):
    model = ContactRole

class ContactRoleAdmin(admin.ModelAdmin):
    model = ContactRole
    list_display_links = ('id',)
    list_display = ('id','contact', 'layer', 'role')
    list_editable = ('contact', 'layer', 'role')

class MapAdmin(admin.ModelAdmin):
    list_display = ('id','title','owner', 'last_modified')
    list_display_links = ('id',)
    list_editable = ('owner',)
    #inlines = [MapLayerInline,]
    exclude = ('tools_params','portal_params')
    list_filter = ('owner',)
    search_fields = ('title',)

class ContactAdmin(admin.ModelAdmin):
    inlines = [ContactRoleInline]

class LayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'typename','service_type','title', 'date', 'date_type', 'owner')
    list_display_links = ('id',)
    list_editable = ('title', 'owner')
    list_filter  = ('date', 'date_type', 'constraints_use', 'owner')
    filter_horizontal = ('contacts',)
    date_hierarchy = 'date'
    readonly_fields = ('uuid', 'typename', 'workspace') 
    inlines = [ContactRoleInline]
    search_fields = ('title', 'typename')

    actions = ['change_poc']

    def change_poc(modeladmin, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(reverse('change_poc', kwargs={"ids": "_".join(selected)}))
    change_poc.short_description = "Change the point of contact for the selected layers"
    

admin.site.register(Map, MapAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Layer, LayerAdmin)
admin.site.register(ContactRole, ContactRoleAdmin)
admin.site.register(MapLayer)
admin.site.register(Role)
