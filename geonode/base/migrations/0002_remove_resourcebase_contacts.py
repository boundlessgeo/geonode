# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_resourcebase_refresh_interval'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resourcebase',
            name='contacts',
        ),
    ]
