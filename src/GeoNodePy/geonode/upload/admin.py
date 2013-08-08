from geonode.upload.models import Upload

from django import forms
from django.contrib import admin
import pprint


def import_link(obj):
    url = obj.get_import_url()
    if url: return "<a href='%s'>Geoserver Importer Link</a>" % url
import_link.short_description = 'Link'
import_link.allow_tags = True


def layer_link(obj):
    if obj.layer:
        return "<a href='%s'>Layer</a>" % obj.layer.get_absolute_url()
layer_link.short_description = 'Layer'
layer_link.allow_tags = True


class UploadAdminForm(forms.ModelForm):
    def __init__(self, *args, **kw):
        super(UploadAdminForm, self).__init__(*args, **kw)
        session = self.instance.get_session()
        if session:
            self.initial['session'] = pprint.pformat(vars(session))

class UploadAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'state', import_link, layer_link, 'upload_dir', 'name')
    date_hierarchy = 'date'
    list_filter = ('user', 'state')
    search_fields = ('user', 'name')
    form = UploadAdminForm
    
admin.site.register(Upload, UploadAdmin)