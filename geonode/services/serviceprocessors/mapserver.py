#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

"""Utilities for enabling ESRI REST Mapserver remote services in geonode."""

import logging
from urlparse import urlsplit
from uuid import uuid4

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from geonode.base.models import Link
from geonode.layers.models import Layer
from geonode.layers.utils import create_thumbnail
from geonode.utils import set_attributes
from arcrest.ags import MapService as ArcMapService
from .. import enumerations
from ..enumerations import CASCADED
from ..enumerations import INDEXED
from .. import models

from . import base

logger = logging.getLogger(__name__)


_esri_types = {
    "esriFieldTypeDouble": "xsd:double",
    "esriFieldTypeString": "xsd:string",
    "esriFieldTypeSmallInteger": "xsd:int",
    "esriFieldTypeInteger": "xsd:int",
    "esriFieldTypeDate": "xsd:dateTime",
    "esriFieldTypeOID": "xsd:long",
    "esriFieldTypeGeometry": "xsd:geometry",
    "esriFieldTypeBlob": "xsd:base64Binary",
    "esriFieldTypeRaster": "raster",
    "esriFieldTypeGUID": "xsd:string",
    "esriFieldTypeGlobalID": "xsd:string",
    "esriFieldTypeXML": "xsd:anyType",
    "esriFieldTypeSingle": "xsd:float"
}


class MapserverServiceHandler(base.ServiceHandlerBase,
                        base.CascadableServiceHandlerMixin):
    """Remote service handler for OGC WMS services"""

    service_type = enumerations.REST

    def __init__(self, url):
        self.parsed_service = ArcMapService(url)
        self.indexing_method = (
            INDEXED if self._offers_geonode_projection() else CASCADED)
        self.url = self.parsed_service.url
        self.title = self.parsed_service.itemInfo['title']
        self.name = _get_valid_name(self.parsed_service.itemInfo['name'])

    def create_cascaded_store(self):
        store = self._get_store(create=True)
        store.capabilitiesURL = self.url
        cat = store.catalog
        cat.save(store)
        return store

    def create_geonode_service(self, owner, parent=None):
        """Create a new geonode.service.models.Service instance

        :arg owner: The user who will own the service instance
        :type owner: geonode.people.models.Profile

        """

        instance = models.Service(
            uuid=str(uuid4()),
            base_url=self.url,
            type=self.service_type,
            method=self.indexing_method,
            owner=owner,
            parent=parent,
            version=self.parsed_service.currentVersion,
            name=self.name,
            title=self.title,
            abstract=self.parsed_service.serviceDescription or _(
                "Not provided"),
            online_resource=self.url,
        )
        return instance

    def get_keywords(self):
        return self.parsed_service.documentInfo['Keywords'].split(',')

    def has_basic_capabilities(self):
        if self.parsed_service.capabilities and 'Tilemap' in self.parsed_service.capabilities:
            return True
        else:
            return False

    def get_resource(self, resource_id):
        return self.parsed_service.layers[int(resource_id)]

    def get_resources(self):
        """Return an iterable with the service's resources.

        For WMS we take into account that some layers are just logical groups
        of metadata and do not return those.

        """

        return list( self.parsed_service.layers)

    def harvest_resource(self, resource_id, geonode_service):
        """Harvest a single resource from the service

        This method will try to create new ``geonode.layers.models.Layer``
        instance (and its related objects too).

        :arg resource_id: The resource's identifier
        :type resource_id: str
        :arg geonode_service: The already saved service instance
        :type geonode_service: geonode.services.models.Service

        """

        layer_meta = self.get_resource(resource_id)
        logger.debug("layer_meta: {}".format(layer_meta))
        if self.indexing_method == CASCADED:
            logger.debug("About to import cascaded layer...")
            geoserver_resource = self._import_cascaded_resource(layer_meta)
            resource_fields = self._get_cascaded_layer_fields(
                geoserver_resource)
            keywords = []
        else:
            resource_fields = self._get_indexed_layer_fields(layer_meta)
            keywords = resource_fields.pop("keywords")
        existance_test_qs = Layer.objects.filter(
            name=resource_fields["name"],
            store=resource_fields["store"],
            workspace=resource_fields["workspace"]
        )
        if existance_test_qs.exists():
            raise RuntimeError(
                "Resource {!r} has already been harvested".format(resource_id))
        # bear in mind that in ``geonode.layers.models`` there is a
        # ``pre_save_layer`` function handler that is connected to the
        # ``pre_save`` signal for the Layer model. This handler does a check
        # for common fields (such as abstract and title) and adds
        # sensible default values
        geonode_layer = Layer(
            owner=geonode_service.owner,
            service=geonode_service,
            uuid=str(uuid4()),
            **resource_fields
        )
        geonode_layer.full_clean()
        geonode_layer.save()
        geonode_layer.keywords.add(*keywords)
        geonode_layer.set_default_permissions()
        self._create_layer_service_link(geonode_layer)
        self._create_layer_legend_link(geonode_layer)
        self._create_layer_thumbnail(geonode_layer)
        self._create_layer_attributes(geonode_layer, layer_meta)
        geonode_layer.save()

    def has_resources(self):
        return True if len(self.parsed_service.layers) > 0 else False

    def _create_layer_thumbnail(self, geonode_layer):
        """Grab the image from the service."""

        thumbnail_remote_url = "{}/info/thumbnail".format(self.url)
        logger.debug("thumbnail_remote_url: {}".format(thumbnail_remote_url))
        create_thumbnail(
            instance=geonode_layer,
            thumbnail_remote_url=thumbnail_remote_url,
            thumbnail_create_url=None,
            check_bbox=False,
            overwrite=True,
        )

    def _create_layer_attributes(self, geonode_layer, layer_meta):
        """Get the layer's field name and types

        Regardless of the service being INDEXED or CASCADED we're always
        creating the layer attributes.

        """

        attribute_map = []
        if layer_meta.fields:
            attribute_map = [[n["name"], _esri_types[n["type"]]]
                             for n in layer_meta.fields if n.get("name") and n.get("type")]

        set_attributes(geonode_layer, attribute_map, overwrite=True)

    def _create_layer_legend_link(self, geonode_layer):
        """Get the layer's legend and save it locally

        Regardless of the service being INDEXED or CASCADED we're always
        creating the legend by making a request directly to the original
        service.

        """

        legend_url = "{}/legend?f=pjson".format(self.url)
        logger.debug("legend_url: {}".format(legend_url))
        Link.objects.get_or_create(
            resource=geonode_layer.resourcebase_ptr,
            url=legend_url,
            defaults={
                "extension": 'json',
                "name": 'Legend',
                "url": legend_url,
                "mime": 'application/json',
                "link_type": 'data',
            }
        )

    def _create_layer_service_link(self, geonode_layer):

        type_mapping = { 'mapserver': 'ESRI:AIMS--http-get-map',
                         'featureserver': 'ESRI:AIMS--http-get-feature',
                         'imageserver': 'ESRI:AIMS--http-get-image',
                         'kmlserver': 'OGC:KML',
                         'wfsserver': 'OGC:WFS',
                         'wmsserver': 'OGC:WMS',
                         }


        # Services don't always have extensions.
        if self.parsed_service.supportedExtensions.strip():
            for supported_extension in self.parsed_service.supportedExtensions.split(','):
                url = geonode_layer.ows_url.strip('/')
                supported_extension = supported_extension.strip()
                if supported_extension == 'WMSServer':
                    url = url.replace('rest/services', 'services')
                    url += '/WMSServer?request=GetCapabilities&amp;service=WMS'
                elif supported_extension == 'KmlServer':
                    url += '/generateKml';
                elif supported_extension == 'FeatureServer':
                    url = url.replace('MapServer', 'FeatureServer')
                elif supported_extension == 'WFSServer':
                    url = url.replace('rest/services', 'services')
                    url += '/WFSServer?request=GetCapabilities&amp;service=WFS';

                link, created = Link.objects.get_or_create(
                    resource=geonode_layer.resourcebase_ptr,
                    url=url,
                    name=supported_extension,
                    defaults={
                        "extension": "html",
                        "mime": "text/html",
                        "link_type": type_mapping[supported_extension.lower()],
                    }
                )

    def _get_cascaded_layer_fields(self, geoserver_resource):
        name = geoserver_resource.name
        workspace = geoserver_resource.workspace.name
        store = geoserver_resource.store
        bbox = geoserver_resource.latlon_bbox
        return {
            "name": name,
            "workspace": workspace,
            "store": store.name,
            "typename": "{}:{}".format(workspace, name),
            "storeType": "remoteStore",  # store.resource_type,
            "title": geoserver_resource.title,
            "abstract": geoserver_resource.abstract,
            "bbox_x0": bbox[0],
            "bbox_x1": bbox[1],
            "bbox_y0": bbox[2],
            "bbox_y1": bbox[3],
        }

    def _get_indexed_layer_fields(self, layer_meta):
        bbox = layer_meta.extent
        layer_name = slugify(layer_meta.name)
        iteminfo_name = slugify(self.parsed_service.itemInfo['name'])
        typename = "{}_{}:{}".format(iteminfo_name, layer_name,
                str(layer_meta.id))

        return {
            "name": "{}_{}".format(iteminfo_name, layer_meta.name),
            "store": self.name,
            "storeType": "remoteStore",
            "workspace": "remoteWorkspace",
            "typename": typename,
            "alternate": layer_meta.id,
            "title": layer_meta.name,
            "abstract": layer_meta.description,
            "bbox_x0": bbox['xmin'],
            "bbox_x1": bbox['xmax'],
            "bbox_y0": bbox['ymin'],
            "bbox_y1": bbox['ymax'],
            "srid": "EPSG:%s" % bbox['spatialReference']['latestWkid'],
            "keywords": self.get_keywords(),
        }

    def _get_store(self, create=True):
        """Return the geoserver store associated with this service.

        The store may optionally be created if it doesn't exist already.
        Store is assumed to be (and created) named after the instance's name
        and belongs to the default geonode workspace for cascaded layers.

        """

        workspace = base.get_geoserver_cascading_workspace(create=create)
        cat = workspace.catalog
        store = cat.get_store(self.name, workspace=workspace)
        logger.debug("name: {}".format(self.name))
        logger.debug("store: {}".format(store))
        if store is None and create:  # store did not exist. Create it
            store = cat.create_wmsstore(
                name=self.name,
                workspace=workspace,
                user=cat.username,
                password=cat.password
            )
        return store

    def _import_cascaded_resource(self, layer_meta):
        """Import a layer into geoserver in order to enable cascading."""
        store = self._get_store(create=False)
        cat = store.catalog
        workspace = store.workspace
        layer_resource = cat.get_resource(layer_meta.id, store, workspace)
        if layer_resource is None:
            layer_resource = cat.create_wmslayer(
                workspace, store, layer_meta.id)
            layer_resource.projection = getattr(
                settings, "DEFAULT_MAP_CRS", "EPSG:3857")
            # Do not use the geoserver.support.REPROJECT enumeration until
            # https://github.com/boundlessgeo/gsconfig/issues/174
            # has been fixed
            layer_resource.projection_policy = "REPROJECT_TO_DECLARED"
            cat.save(layer_resource)
            if layer_resource is None:
                raise RuntimeError("Could not cascade resource {!r} through "
                                   "geoserver".format(layer_meta))
        else:
            logger.info("Layer {} is already present. Skipping...".format(
                layer_meta.id))
        return layer_resource

    def _offers_geonode_projection(self):
        geonode_projection = getattr(settings, "DEFAULT_MAP_CRS", "EPSG:4326")
        layers = list(self.get_resources())
        if len(layers) > 0:
            #str(layers[0].extent['spatialReference']['wkid']) in geonode_projection
            return True
        else:
            return False


def _get_valid_name(proposed_name):
    """Return a unique slug name for a service"""
    slug_name = slugify(proposed_name)
    name = slug_name
    if len(slug_name) > 40:
        name = slug_name[:40]
    return name
