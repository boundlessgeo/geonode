# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0032_auto_20190319_0400'),
    ]

    def combine_description_abstract(apps, schema_editor):
        Service = apps.get_model("services", "Service")
        for service in Service.objects.all():
            if service.description is not None:
                service.abstract = "{0}\n\nDescription: {1}".format(
                    service.abstract, service.description)
                service.description = None
                service.save()

    operations = [
        migrations.RunPython(combine_description_abstract),
        migrations.RemoveField(
            model_name='service',
            name='description',
        ),
    ]
