# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layers', '0032_layer_visibility'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layer',
            name='elevation_regex',
            field=models.CharField(help_text='the elevation regex applied to the layer data', max_length=128, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='layer',
            name='has_elevation',
            field=models.BooleanField(default=False, help_text='indicates elevation data layer'),
        ),
        migrations.AlterField(
            model_name='layer',
            name='has_time',
            field=models.BooleanField(default=False, help_text='indicates time enabled layer'),
        ),
        migrations.AlterField(
            model_name='layer',
            name='is_mosaic',
            field=models.BooleanField(default=False, help_text='indicates mosaic data layer'),
        ),
        migrations.AlterField(
            model_name='layer',
            name='time_regex',
            field=models.CharField(blank=True, max_length=128, null=True, help_text='the time regex applied to the layer data', choices=[(b'[0-9]{8}', 'YYYYMMDD'), (b'[0-9]{8}T[0-9]{6}', "YYYYMMDD'T'hhmmss"), (b'[0-9]{8}T[0-9]{6}Z', "YYYYMMDD'T'hhmmss'Z'")]),
        ),
    ]
