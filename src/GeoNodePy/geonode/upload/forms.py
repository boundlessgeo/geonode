from django import forms
from django.conf import settings
from geonode.maps.forms import JSONField
import os
import tempfile

class LayerUploadForm(forms.Form):
    base_file = forms.FileField()
    dbf_file = forms.FileField(required=False)
    shx_file = forms.FileField(required=False)
    prj_file = forms.FileField(required=False)
    sld_file = forms.FileField(required=False)

    abstract = forms.CharField(required=False)
    layer_title = forms.CharField(required=False)
    permissions = JSONField()

    spatial_files = ("base_file", "dbf_file", "shx_file", "prj_file", "sld_file")

    def clean(self):
        cleaned = super(LayerUploadForm, self).clean()
        base_name, base_ext = os.path.splitext(cleaned["base_file"].name)
        if base_ext.lower() == '.zip':
            # for now, no verification, but this could be unified
            pass
        elif base_ext.lower() not in (".shp", ".tif", ".tiff", ".geotif", ".geotiff", ".csv"):
            raise forms.ValidationError("Only Shapefiles, GeoTiffs, and CSV files are supported. You uploaded a %s file" % base_ext)
        if base_ext.lower() == ".shp":
            dbf_file = cleaned["dbf_file"]
            shx_file = cleaned["shx_file"]
            if dbf_file is None or shx_file is None:
                raise forms.ValidationError("When uploading Shapefiles, .SHX and .DBF files are also required.")
            dbf_name, __ = os.path.splitext(dbf_file.name)
            shx_name, __ = os.path.splitext(shx_file.name)
            if dbf_name != base_name or shx_name != base_name:
                raise forms.ValidationError("It looks like you're uploading "
                    "components from different Shapefiles. Please "
                    "double-check your file selections.")
            if cleaned["prj_file"] is not None:
                prj_file = cleaned["prj_file"].name
                if os.path.splitext(prj_file)[0] != base_name:
                    raise forms.ValidationError("It looks like you're "
                        "uploading components from different Shapefiles. "
                        "Please double-check your file selections.")
        return cleaned

    def write_files(self):
        tempdir = tempfile.mkdtemp(dir=settings.FILE_UPLOAD_TEMP_DIR)
        for field in self.spatial_files:
            f = self.cleaned_data[field]
            if f is not None:
                path = os.path.join(tempdir, f.name)
                with open(path, 'w') as writable:
                    for c in f.chunks():
                        writable.write(c)
        absolute_base_file = os.path.join(tempdir,
                self.cleaned_data["base_file"].name)
        return tempdir, absolute_base_file


class TimeForm(forms.Form):
    presentation_strategy = forms.CharField(required=False)
    precision_value = forms.IntegerField(required=False)
    attribute_format = forms.CharField(required=False)
    end_attribute_format = forms.CharField(required=False)
    precision_step = forms.ChoiceField(required=False, choices=[
        ('years',)*2,
        ('months',)*2,
        ('days',)*2,
        ('hours',)*2,
        ('minutes',)*2,
        ('seconds',)*2
    ])

    def __init__(self, *args, **kwargs):
        # have to remove these from kwargs or Form gets mad
        attributes = kwargs.pop('attributes', None)
        super(TimeForm, self).__init__(*args, **kwargs)
        # dynamically build both choice fields from the attributes provided
        if attributes:
            attributes.sort()
            attributes = [ '%s [%s]' % i for i in attributes ]
            choices = [('', '<None>')] + [(a, a) for a in attributes]
            self.fields['attribute'] = forms.ChoiceField(choices=choices, required=False)
            self.fields['end_attribute'] = forms.ChoiceField(choices=choices, required=False)

    # @todo implement clean


class SRSForm(forms.Form):
    srs = forms.CharField(required=True)
