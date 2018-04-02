# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0027_auto_20180313_1430'),
    ]

    operations = [
        migrations.AddField(
            model_name='map',
            name='map_params',
            field=models.TextField(verbose_name='map params', blank=True),
        ),
    ]
