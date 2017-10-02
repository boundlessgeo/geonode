# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '24_initial')
    ]

    operations = [
        migrations.AddField(
            model_name='Map',
            name='renderer',
            field=models.CharField(max_length=32, verbose_name='Renderer', blank=True)
        )
    ]
