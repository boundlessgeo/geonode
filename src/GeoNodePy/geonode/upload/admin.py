from geonode.upload.models import Upload

from django import forms
from django.contrib import admin
import pprint


def import_link(obj):
        return "<a href='%s'>Geoserver Importer Link</a>" % obj.get_import_url()
import_link.short_description = 'Link'
import_link.allow_tags = True


class UploadAdminForm(forms.ModelForm):
    def __init__(self, *args, **kw):
        super(UploadAdminForm, self).__init__(*args, **kw)
        session = self.instance.get_session()
        print session
        if session:
            self.initial['session'] = pprint.pformat(vars(session))

class UploadAdmin(admin.ModelAdmin):
    list_display = ('user','date', 'state', import_link)
    date_hierarchy = 'date'
    list_filter = ('user','state')
    form = UploadAdminForm
    
admin.site.register(Upload, UploadAdmin)