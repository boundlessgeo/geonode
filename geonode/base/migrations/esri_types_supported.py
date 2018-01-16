# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0027_auto_20170801_1228'),
    ]

    operations = [
        migrations.AlterField(
            model_name='link',
            name='link_type',
            field=models.CharField(max_length=255, choices=[(b'original', b'original'), (b'data', b'data'), (b'image', b'image'), (b'metadata', b'metadata'), (b'html', b'html'), (b'OGC:WMS', b'OGC:WMS'), (b'OGC:WFS', b'OGC:WFS'), (b'OGC:WCS', b'OGC:WCS'), (b'OGC:KML', b'OGC:KML'), (b'ESRI:AIMS--http-get-map', b'ESRI:AIMS--http-get-map'), (b'ESRI:AIMS--http-get-feature', b'ESRI:AIMS--http-get-feature'), (b'ESRI:AIMS--http-get-image', b'ESRI:AIMS--http-get-image')]),
        ),
    ]
