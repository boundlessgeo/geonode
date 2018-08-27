# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '24_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='content_creator',
            field=models.BooleanField(default=True, help_text='User can upload layers and documents', verbose_name='Content Creator'),
        ),
        migrations.AddField(
            model_name='profile',
            name='content_manager',
            field=models.BooleanField(default=True, help_text='User can register remote services', verbose_name='Content Creator'),
        ),
    ]
