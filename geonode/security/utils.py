# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2018 OSGeo
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
from geonode import geoserver
from geonode.decorators import on_ogc_backend
from lxml import etree

try:
    import json
except ImportError:
    from django.utils import simplejson as json
import logging
import traceback
import requests
import models
from requests.auth import HTTPBasicAuth
from urlparse import urlparse, parse_qsl
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib import urlencode

from django.conf import settings
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
# from django.contrib.auth import login
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from guardian.utils import get_user_obj_perms_model
from guardian.shortcuts import assign_perm
from geonode.groups.models import GroupProfile
from ..services.enumerations import CASCADED

try:
    geofence_url = settings.GEOFENCE['url'].strip('/')
except AttributeError:
    geofence_url = "{}/geofence".format(settings.OGC_SERVER['default']['LOCATION'].strip('/'))

try:
    geofence_username = settings.GEOFENCE['username']
except AttributeError:
    geofence_username = settings.OGC_SERVER['default']['USER']

try:
    geofence_password = settings.GEOFENCE['password']
except AttributeError:
    geofence_password = settings.OGC_SERVER['default']['PASSWORD']

internal_geofence = settings.OGC_SERVER['default']['LOCATION'] in geofence_url
logger = logging.getLogger("geonode.security.utils")


http_client = requests.session()
http_client.verify = True
parsed_url = urlparse(geofence_url)
retry = Retry(
    total=4,
    status=4,
    backoff_factor=0.9,
    status_forcelist=[502, 503, 504],
    method_whitelist=set(['HEAD', 'TRACE', 'GET', 'PUT', 'POST', 'OPTIONS', 'DELETE'])
)

http_client.mount("{}://".format(parsed_url.scheme), HTTPAdapter(max_retries=retry))


def http_request(url, data=None, method='get', headers={}, access_token=None):
    req_method = getattr(http_client, method.lower())
    resp = None

    if access_token:
        headers['Authorization'] = "Bearer {}".format(access_token)
        parsed_url = urlparse(url)
        params = parse_qsl(parsed_url.query.strip())
        params.append(('access_token', access_token))
        params = urlencode(params)
        url = "{proto}://{address}{path}?{params}".format(proto=parsed_url.scheme, address=parsed_url.netloc,
                                                          path=parsed_url.path, params=params)

        try:
            resp = req_method(url, headers=headers, data=data)
        except:
            logger.debug(traceback.format_exc())
    else:
        try:
            resp = req_method(url, headers=headers, data=data, auth=(geofence_username, geofence_password))
        except:
            logger.debug(traceback.format_exc())

    return resp


def get_visible_resources(queryset,
                          user,
                          admin_approval_required=False,
                          unpublished_not_visible=False,
                          private_groups_not_visibile=False):
    is_admin = False
    is_manager = False
    if user:
        is_admin = user.is_superuser if user else False
        try:
            is_manager = user.groupmember_set.all().filter(role='manager').exists()
        except BaseException:
            is_manager = False

    # Get the list of objects the user has access to
    anonymous_group = None
    public_groups = GroupProfile.objects.exclude(access="private").values('group')
    groups = []
    group_list_all = []
    manager_groups = []
    try:
        group_list_all = user.group_list_all().values('group')
    except BaseException:
        pass
    try:
        manager_groups = Group.objects.filter(
            name__in=user.groupmember_set.filter(role="manager").values_list("group__slug", flat=True))
    except BaseException:
        pass
    try:
        anonymous_group = Group.objects.get(name='anonymous')
        if anonymous_group and anonymous_group not in groups:
            groups.append(anonymous_group)
    except BaseException:
        pass

    filter_set = queryset

    if admin_approval_required:
        if not is_admin:
            if is_manager:
                filter_set = filter_set.filter(
                    Q(is_published=True) |
                    Q(group__in=groups) |
                    Q(group__in=manager_groups) |
                    Q(group__in=group_list_all) |
                    Q(group__in=public_groups) |
                    Q(owner__username__iexact=str(user)))
            elif user:
                filter_set = filter_set.filter(
                    Q(is_published=True) |
                    Q(group__in=groups) |
                    Q(group__in=group_list_all) |
                    Q(group__in=public_groups) |
                    Q(owner__username__iexact=str(user)))
            else:
                filter_set = filter_set.filter(
                    Q(is_published=True) |
                    Q(group__in=public_groups) |
                    Q(group__in=groups))

    if unpublished_not_visible:
        if not is_admin:
            if user:
                filter_set = filter_set.exclude(
                    Q(is_published=False) & ~(
                        Q(owner__username__iexact=str(user)) | Q(group__in=group_list_all)))
            else:
                filter_set = filter_set.exclude(is_published=False)

    if private_groups_not_visibile:
        if not is_admin:
            private_groups = GroupProfile.objects.filter(access="private").values('group')
            if user:
                filter_set = filter_set.exclude(
                    Q(group__in=private_groups) & ~(
                        Q(owner__username__iexact=str(user)) | Q(group__in=group_list_all)))
            else:
                filter_set = filter_set.exclude(group__in=private_groups)

    return filter_set


def get_users_with_perms(obj):
    """
    Override of the Guardian get_users_with_perms
    """
    ctype = ContentType.objects.get_for_model(obj)
    permissions = {}
    PERMISSIONS_TO_FETCH = models.ADMIN_PERMISSIONS + models.LAYER_ADMIN_PERMISSIONS

    for perm in Permission.objects.filter(codename__in=PERMISSIONS_TO_FETCH, content_type_id=ctype.id):
        permissions[perm.id] = perm.codename

    user_model = get_user_obj_perms_model(obj)
    users_with_perms = user_model.objects.filter(object_pk=obj.pk,
                                                 content_type_id=ctype.id,
                                                 permission_id__in=permissions).values('user_id', 'permission_id')

    users = {}
    for item in users_with_perms:
        if item['user_id'] in users:
            users[item['user_id']].append(permissions[item['permission_id']])
        else:
            users[item['user_id']] = [permissions[item['permission_id']], ]

    profiles = {}
    for profile in get_user_model().objects.filter(id__in=users.keys()):
        profiles[profile] = users[profile.id]

    return profiles


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def get_geofence_rules_count():
    """Get the number of available GeoFence Cache Rules"""
    try:
        # Check first that the rules does not exist already
        """
        curl -X GET -u admin:geoserver \
              http://<host>:<port>/geoserver/geofence/rest/rules/count.json
        """
        resp = http_request("{}/rules/count.json".format(geofence_url))
        if resp.status_code == 200:
            rules_objs = resp.json()
            rules_count = rules_objs['count']
            return int(rules_count)
        else:
            logger.error("Failed to retrieve GeoFence rule count")
            return -1
    except BaseException:
        tb = traceback.format_exc()
        logger.debug(tb)
        return -1


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def get_highest_priority():
    """Get the highest Rules priority"""
    try:
        # Check first that the rules does not exist already
        """
        curl -X GET -u admin:geoserver \
              http://<host>:<port>/geoserver/geofence/rest/rules.json?page=(count-1)&entries=1
        """
        rules_count = get_geofence_rules_count()
        resp = http_request("{}/rules.json?page={}&entries=1".format(geofence_url, rules_count))
        if resp.status_code == 200:
            rules_objs = resp.json()
            if len(rules_objs['rules']) > 0:
                highest_priority = rules_objs['rules'][0]['priority']
            else:
                highest_priority = 0
            return int(highest_priority)
        else:
            logger.error("Failed to retrieve GeoFence rule count")
            return -1
    except BaseException:
        tb = traceback.format_exc()
        logger.debug(tb)
        return -1


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def purge_geofence_all():
    """purge all existing GeoFence Cache Rules"""
    if settings.OGC_SERVER['default']['GEOFENCE_SECURITY_ENABLED']:
        try:
            """
            curl -X GET -u admin:geoserver -H "Content-Type: application/json" \
                  http://<host>:<port>/geoserver/geofence/rest/rules.json
            """
            headers = {'Content-type': 'application/json'}
            resp = http_request("{}/rules.json".format(geofence_url))
            if resp.status_code == 200:
                try:
                    rules_objs = resp.json()
                    rules_count = rules_objs['count']
                    rules = rules_objs['rules']
                    if rules_count > 0:
                        # Delete GeoFence Rules associated to the Layer
                        # curl -X DELETE -u admin:geoserver http://<host>:<port>/geoserver/geofence/rest/rules/id/{r_id}
                        for i, rule in enumerate(rules):
                            rule_url = "{}/rules/id/{}".format(geofence_url, rule['id'])
                            resp = http_request(
                                rule_url,
                                method='delete',
                                headers=headers
                            )
                            if resp.status_code != 200:
                                msg = "Could not DELETE GeoServer Rule id[%s]".format(rule['id'])
                                logger.error(msg)
                                logger.debug("Response [{}] : {}".format(resp.status_code, resp.text))
                                raise Exception(msg)
                except Exception:
                    logger.debug("Response [{}] : {}".format(resp.status_code, resp.text))
            else:
                logger.warning("Could not Retrieve GeoFence Rules")
        except Exception:
            tb = traceback.format_exc()
            logger.debug(tb)


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def purge_geofence_layer_rules(resource):
    """purge layer existing GeoFence Cache Rules"""
    # Scan GeoFence Rules associated to the Layer
    """
    curl -u admin:geoserver
    http://<host>:<port>/geoserver/geofence/rest/rules.json?workspace=geonode&layer={layer}
    """
    headers = {'Content-type': 'application/json'}
    workspace = _get_layer_workspace(resource.layer)
    resp = http_request("{}/rules.json?workspace={}&layer={}".format(
            geofence_url, workspace, resource.layer.name))

    if resp.status_code == 200:
        gs_rules = resp.json()
        r_ids = []
        if gs_rules and gs_rules['rules']:
            for r in gs_rules['rules']:
                if r['layer'] and r['layer'] == resource.layer.name:
                    r_ids.append(r['id'])

        # Delete GeoFence Rules associated to the Layer
        # curl -X DELETE -u admin:geoserver http://<host>:<port>/geoserver/geofence/rest/rules/id/{r_id}
        for i, r_id in enumerate(r_ids):
            rule_url = "{}/rules/id/{}".format(geofence_url, r_id)
            resp = http_request(
                rule_url,
                method='delete',
                headers=headers
            )
            if resp.status_code != 200:
                msg = "Could not DELETE GeoServer Rule for Layer {}".format(resource.layer.name)
                logger.error(msg)
                logger.debug("Response [{}] : {}".format(resp.status_code, resp.text))
                raise Exception(msg)


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def set_geofence_invalidate_cache():
    """invalidate GeoFence Cache Rules"""
    if settings.OGC_SERVER['default']['GEOFENCE_SECURITY_ENABLED']:
        try:
            url = "{}/rest/ruleCache/invalidate".format(settings.OGC_SERVER['default']['LOCATION'].strip('/'))
            # Check first that the rules does not exist already
            """
            curl -X GET -u admin:geoserver \
                  http://<host>:<port>/geoserver/rest/ruleCache/invalidate
            """
            resp = http_request(
                url,
                method='put'
            )
            if resp.status_code not in (200, 201):
                logger.error("Could not Invalidate GeoFence Rules.")
        except Exception:
            tb = traceback.format_exc()
            logger.debug(tb)


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def set_geowebcache_invalidate_cache(layer_alternate):
    """invalidate GeoWebCache Cache Rules"""
    try:
        url = settings.OGC_SERVER['default']['LOCATION']
        user = settings.OGC_SERVER['default']['USER']
        passwd = settings.OGC_SERVER['default']['PASSWORD']
        # Check first that the rules does not exist already
        """
        curl -v -u admin:geoserver \
            -H "Content-type: text/xml" \
            -d "<truncateLayer><layerName>{layer_alternate}</layerName></truncateLayer>" \
            http://localhost:8080/geoserver/gwc/rest/masstruncate
        """
        headers = {'Content-type': 'text/xml'}
        payload = "<truncateLayer><layerName>%s</layerName></truncateLayer>" % layer_alternate
        r = requests.post(url + 'gwc/rest/masstruncate',
                          headers=headers,
                          data=payload,
                          auth=HTTPBasicAuth(user, passwd))
        if (r.status_code < 200 or r.status_code > 201):
            logger.warning("Could not Truncate GWC Cache for Layer '%s'." % layer_alternate)
    except Exception:
        tb = traceback.format_exc()
        logger.debug(tb)


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def set_geofence_all(instance):
    """assign access permissions to all users

    This method is only relevant to Layer instances that have their
    underlying data managed by geoserver, meaning:

    * layers that are not associated with a Service
    * layers that are associated with a Service that is being CASCADED through
      geoserver

    """

    resource = instance.get_self_resource()
    logger.debug("Inside set_geofence_all for instance {}".format(instance))
    try:
        workspace = _get_layer_workspace(resource.layer)
        logger.debug("going to work in workspace {!r}".format(workspace))
    except (ObjectDoesNotExist, AttributeError, RuntimeError):
        # This is either not a layer (if raised AttributeError) or it is
        # a layer that is not manageable by geofence (if raised
        # RuntimeError) so we have nothing to do
        return
    try:
        # Create GeoFence Rules for ANONYMOUS to the Layer
        """
        curl -X POST -u admin:geoserver -H "Content-Type: text/xml" -d \
        "<Rule><workspace>geonode</workspace><layer>{layer}</layer><access>ALLOW</access></Rule>" \
        http://<host>:<port>/geoserver/geofence/rest/rules
        """
        headers = {'Content-type': 'application/xml'}
        rule = _get_geofence_payload(
            layer=resource.layer.name,
            workspace=workspace,
            access="ALLOW"
        )

        rules_url = "{}/rules".format(geofence_url)
        resp = http_request(
            rules_url,
            method='post',
            headers=headers,
            data=rule
        )

        if resp.status_code not in (200, 201):
            logger.error("Could not ADD GeoServer ANONYMOUS Rule "
                         "for Layer {}".format(resource.layer.name))
            logger.debug(
                "Response {!r} : {}".format(resp.status_code, resp.text))
            raise RuntimeError("Could not ADD GeoServer ANONYMOUS Rule "
                               "for Layer {}".format(resource.layer.name))
    except Exception:
        tb = traceback.format_exc()
        logger.debug(tb)
    finally:
        set_geofence_invalidate_cache()


@on_ogc_backend(geoserver.BACKEND_PACKAGE)
def sync_geofence_with_guardian(layer, perms, user=None, group=None):
    """
    Sync Guardian permissions to GeoFence.
    """
    # Create new rule-set
    gf_services = {}
    gf_services["*"] = 'download_resourcebase' in perms and \
        ('view_resourcebase' in perms or 'change_layer_style' in perms)
    gf_services["WMS"] = 'view_resourcebase' in perms or 'change_layer_style' in perms
    gf_services["GWC"] = 'view_resourcebase' in perms or 'change_layer_style' in perms
    gf_services["WFS"] = ('download_resourcebase' in perms or 'change_layer_data' in perms) \
        and layer.is_vector()
    gf_services["WCS"] = ('download_resourcebase' in perms or 'change_layer_data' in perms) \
        and not layer.is_vector()
    gf_services["WPS"] = 'download_resourcebase' or 'change_layer_data' in perms

    _user = None
    if user:
        _user = user if isinstance(user, basestring) else user.username
    _group = None
    if group:
        _group = group if isinstance(group, basestring) else group.name
    for service, allowed in gf_services.iteritems():
        if allowed:
            if _user:
                logger.debug("Adding 'user' to geofence the rule: %s %s %s" % (layer, service, _user))
                _update_geofence_rule(layer.name, layer.workspace, service, user=_user)
            elif not _group:
                logger.debug("Adding to geofence the rule: %s %s *" % (layer, service))
                _update_geofence_rule(layer.name, layer.workspace, service)

            if _group:
                logger.debug("Adding 'group' to geofence the rule: %s %s %s" % (layer, service, _group))
                _update_geofence_rule(layer.name, layer.workspace, service, group=_group)
    set_geofence_invalidate_cache()


def set_owner_permissions(resource):
    """assign all admin permissions to the owner"""
    if resource.polymorphic_ctype:
        # Set the GeoFence Owner Rule
        if resource.polymorphic_ctype.name == 'layer':
            for perm in models.LAYER_ADMIN_PERMISSIONS:
                assign_perm(perm, resource.owner, resource.layer)
        for perm in models.ADMIN_PERMISSIONS:
            assign_perm(perm, resource.owner, resource.get_self_resource())


def remove_object_permissions(instance):
    """Remove object permissions on given resource.

    If is a layer removes the layer specific permissions then the
    resourcebase permissions

    """

    from guardian.models import UserObjectPermission, GroupObjectPermission
    resource = instance.get_self_resource()
    if hasattr(resource, "layer"):
        try:
            UserObjectPermission.objects.filter(
                content_type=ContentType.objects.get_for_model(resource.layer),
                object_pk=instance.id
            ).delete()
            GroupObjectPermission.objects.filter(
                content_type=ContentType.objects.get_for_model(resource.layer),
                object_pk=instance.id
            ).delete()
            if settings.OGC_SERVER['default']['GEOFENCE_SECURITY_ENABLED']:
                purge_geofence_layer_rules(resource)
        except (ObjectDoesNotExist, RuntimeError):
            pass  # This layer is not manageable by geofence
        except Exception:
            tb = traceback.format_exc()
            logger.debug(tb)
        finally:
            set_geofence_invalidate_cache()

    UserObjectPermission.objects.filter(content_type=ContentType.objects.get_for_model(resource),
                                        object_pk=instance.id).delete()
    GroupObjectPermission.objects.filter(content_type=ContentType.objects.get_for_model(resource),
                                         object_pk=instance.id).delete()


# # Logic to login a user automatically when it has successfully
# # activated an account:
# def autologin(sender, **kwargs):
#     user = kwargs['user']
#     request = kwargs['request']
#     # Manually setting the default user backed to avoid the
#     # 'User' object has no attribute 'backend' error
#     user.backend = 'django.contrib.auth.backends.ModelBackend'
#     # This login function does not need password.
#     login(request, user)
#
# # FIXME(Ariel): Replace this signal with the one from django-user-accounts
# # user_activated.connect(autologin)


def _get_layer_workspace(layer):
    """Get the workspace where the input layer belongs"""
    workspace = layer.workspace
    if not workspace:
        default_workspace = getattr(settings, "DEFAULT_WORKSPACE", "geonode")
        try:
            if layer.remote_service.method == CASCADED:
                workspace = getattr(
                    settings, "CASCADE_WORKSPACE", default_workspace)
            else:
                raise RuntimeError("Layer is not cascaded")
        except AttributeError:  # layer does not have a service
            workspace = default_workspace
    return workspace


def _get_geofence_payload(layer, workspace, access, user=None, group=None,
                          service=None):
    highest_priority = get_highest_priority()
    root_el = etree.Element("Rule")
    username_el = etree.SubElement(root_el, "userName")
    if user is not None:
        username_el.text = user
    else:
        username_el.text = ''
    priority_el = etree.SubElement(root_el, "priority")
    priority_el.text = str(highest_priority if highest_priority >= 0 else 0)
    if group is not None:
        role_el = etree.SubElement(root_el, "roleName")
        role_el.text = "ROLE_{}".format(group.upper())
    workspace_el = etree.SubElement(root_el, "workspace")
    workspace_el.text = workspace
    layer_el = etree.SubElement(root_el, "layer")
    layer_el.text = layer
    access_el = etree.SubElement(root_el, "access")
    access_el.text = access
    if service is not None and service is not "*":
        service_el = etree.SubElement(root_el, "service")
        service_el.text = service
    return etree.tostring(root_el)


def _update_geofence_rule(layer, workspace, service, user=None, group=None):
    rule = _get_geofence_payload(
        layer=layer,
        workspace=workspace,
        access="ALLOW",
        user=user,
        group=group,
        service=service
    )

    logger.debug("request data: {}".format(rule))
    headers = {'Content-type': 'application/xml'}
    rules_url = "{}/rules".format(geofence_url)
    resp = http_request(
        rules_url,
        method='post',
        headers=headers,
        data=rule
    )

    logger.debug("response status_code: {}".format(resp.status_code))
    if resp.status_code not in (200, 201):
        msg = ("Could not ADD GeoServer User {!r} Rule for "
               "Layer {!r}: '{!r}'".format(user, layer, resp.text))
        if 'Duplicate Rule' in resp.text:
            logger.warning(msg)
        else:
            logger.error(msg)
            raise RuntimeError(msg)