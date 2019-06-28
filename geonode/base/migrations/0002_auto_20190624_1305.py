# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_resourcebase_refresh_interval'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resourcebase',
            name='refresh_interval',
            field=models.IntegerField(default=60000, help_text='Time in milliseconds to refresh data on the map viewer', null=True, blank=True),
        ),
    ]
