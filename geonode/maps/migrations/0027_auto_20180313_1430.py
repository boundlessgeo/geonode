# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0026_auto_20180312_1512'),
    ]

    operations = [
        migrations.AddField(
            model_name='map',
            name='bearing',
            field=models.IntegerField(default=0, null=True, verbose_name='bearing', blank=True),
        ),
        migrations.AddField(
            model_name='map',
            name='glyphs',
            field=models.CharField(max_length=255, null=True, verbose_name='glyphs', blank=True),
        ),
        migrations.AddField(
            model_name='map',
            name='light',
            field=models.TextField(null=True, verbose_name='light', blank=True),
        ),
        migrations.AddField(
            model_name='map',
            name='name',
            field=models.CharField(max_length=255, null=True, verbose_name='name', blank=True),
        ),
        migrations.AddField(
            model_name='map',
            name='pitch',
            field=models.IntegerField(default=0, null=True, verbose_name='pitch', blank=True),
        ),
        migrations.AddField(
            model_name='map',
            name='sprite',
            field=models.CharField(max_length=255, null=True, verbose_name='sprite', blank=True),
        ),
        migrations.AddField(
            model_name='map',
            name='transition',
            field=models.TextField(null=True, verbose_name='light', blank=True),
        ),
        migrations.AddField(
            model_name='map',
            name='version',
            field=models.IntegerField(default=0, null=True, blank=True),
        ),
    ]
