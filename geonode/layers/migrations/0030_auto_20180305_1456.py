# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layers', '0029_layer_service'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttributeOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.TextField(help_text='the option value that will be stored in the db when selected by the user', verbose_name='value')),
                ('label', models.TextField(help_text='the option label that is shown to the user in the dropdown', verbose_name='label')),
            ],
        ),
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
        migrations.AddField(
            model_name='attributeoption',
            name='attribute',
            field=models.ForeignKey(related_name='options', to='layers.Attribute'),
        ),
        migrations.AddField(
            model_name='attributeoption',
            name='layer',
            field=models.ForeignKey(to='layers.Layer'),
        ),
    ]
