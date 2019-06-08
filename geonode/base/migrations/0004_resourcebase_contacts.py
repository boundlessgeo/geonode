# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_auto_20190607_1043'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcebase',
            name='contacts',
            field=models.ManyToManyField(to='base.ContactRole', null=True, blank=True),
        ),
    ]
