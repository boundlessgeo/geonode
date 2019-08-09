# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0025_auto_20170801_1228'),
    ]

    operations = [
        migrations.AlterField(
            model_name='map',
            name='featuredurl',
            field=models.CharField(help_text='Featured url name for a full map view or detail view, i.e. featured/featuredurl', max_length=255, verbose_name='Featured Map URL', blank=True),
        ),
        migrations.AlterField(
            model_name='map',
            name='urlsuffix',
            field=models.CharField(help_text='Alphanumeric alternative to referencing maps by id, allowing you to access the map as maps/urlsuffix', max_length=255, verbose_name='Site URL', blank=True),
        ),
    ]
