# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from urlparse import urlsplit, parse_qs


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0031_auto_20180809_1500'),
    ]

    def determine_base_url(apps, schema_editor):
        def is_wfs_url(url):
            if 'WFSServer' in urlsplit(url).path:
                return True
            elif 'geoserver' in urlsplit(url).path:
                query = parse_qs(urlsplit(url).query)
                if 'service' in query:
                    if query['service'] is 'wfs':
                        return True
            return False

        def is_featureserver_url(url):
            if 'FeatureServer' in urlsplit(url).path:
                return True
            return False

        Service = apps.get_model("services", "Service")
        for service in Service.objects.all():
            if service.type == "REST":
                if is_featureserver_url(service.base_url):
                    service.wfs_url = service.base_url
                else:
                    service.wms_url = service.base_url
            else:
                if is_wfs_url(service.base_url):
                    service.wfs_url = service.base_url
                else:
                    service.wms_url = service.base_url
            service.save()

    operations = [
        migrations.AddField(
            model_name='service',
            name='wfs_url',
            field=models.URLField(db_index=True, unique=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='service',
            name='wms_url',
            field=models.URLField(db_index=True, unique=True, null=True, blank=True),
        ),
        migrations.RunPython(determine_base_url),
    ]
