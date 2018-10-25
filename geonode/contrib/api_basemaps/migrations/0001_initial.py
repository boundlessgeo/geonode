# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import geonode.utils


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MapBaseLayer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200, null=True, verbose_name='name')),
                ('provider', models.CharField(max_length=200, null=True, verbose_name='provider')),
                ('stack_order', models.IntegerField(verbose_name='stack order')),
                ('format', models.CharField(max_length=200, null=True, verbose_name='format', blank=True)),
                ('opacity', models.FloatField(default=1.0, verbose_name='opacity')),
                ('styles', models.CharField(max_length=200, null=True, verbose_name='styles', blank=True)),
                ('transparent', models.BooleanField(default=False, verbose_name='transparent')),
                ('fixed', models.BooleanField(default=False, verbose_name='fixed')),
                ('group', models.CharField(max_length=200, null=True, verbose_name='group', blank=True)),
                ('visibility', models.BooleanField(default=True, verbose_name='visibility')),
                ('ows_url', models.URLField(null=True, verbose_name='ows URL', blank=True)),
                ('layer_params', models.TextField(verbose_name='layer params')),
                ('source_params', models.TextField(verbose_name='source params')),
                ('local', models.BooleanField(default=False)),
                ('enabled', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['stack_order'],
                'verbose_name': 'Basemaps',
                'verbose_name_plural': 'Basemaps',
            },
            bases=(models.Model, geonode.utils.GXPLayerBase),
        ),
    ]
