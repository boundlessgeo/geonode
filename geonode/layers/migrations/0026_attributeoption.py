# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layers', '0025_auto_20170502_1050'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttributeOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.TextField(help_text='the option value that will be stored in the db when selected by the user', verbose_name='value')),
                ('label', models.TextField(help_text='the option label that is shown to the user in the dropdown', verbose_name='label')),
                ('attribute', models.ForeignKey(related_name='options', to='layers.Attribute')),
                ('layer', models.ForeignKey(to='layers.Layer')),
            ],
        ),
    ]
