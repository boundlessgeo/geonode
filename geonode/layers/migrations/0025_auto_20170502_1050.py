# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layers', '24_to_26'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='readonly',
            field=models.BooleanField(default=False, help_text='specifies if the attribute should be readonly in editing views', verbose_name='readonly?'),
        ),
        migrations.AddField(
            model_name='attribute',
            name='required',
            field=models.BooleanField(default=False, help_text='specifies if the attribute should be required in editing views', verbose_name='required?'),
        ),
    ]
