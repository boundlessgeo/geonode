# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layers', '0030_auto_20180305_1456'),
    ]

    operations = [
        migrations.CreateModel(
            name='Constraint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('initial_value', models.CharField(default=b'', max_length=255, blank=True)),
                ('is_integer', models.BooleanField(default=False)),
                ('minimum', models.BigIntegerField(null=True, blank=True)),
                ('maximum', models.BigIntegerField(null=True, blank=True)),
                ('minimum_length', models.BigIntegerField(null=True, blank=True)),
                ('maximum_length', models.BigIntegerField(null=True, blank=True)),
                ('regex', models.CharField(max_length=1024, blank=True)),
                ('control_type', models.CharField(blank=True, max_length=128, null=True, choices=[(b'string', b'string'), (b'number', b'number'), (b'date', b'date'), (b'boolean', b'boolean'), (b'select', b'select'), (b'slider', b'slider'), (b'counter', b'counter'), (b'photo', b'photo')])),
                ('attribute', models.OneToOneField(related_name='constraints', to='layers.Attribute')),
            ],
        ),
    ]
