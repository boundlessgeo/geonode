# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', 'esri_types_supported'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcebase',
            name='refresh_interval',
            field=models.IntegerField(default=60000, null=True, blank=True),
        ),
    ]
