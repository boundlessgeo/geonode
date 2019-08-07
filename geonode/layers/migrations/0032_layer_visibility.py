# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layers', '0031_constraint'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='visibility',
            field=models.BooleanField(default=True),
        ),
    ]
