# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2016 OSGeo
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

from django.http import HttpResponse
from urlparse import urlsplit, parse_qsl, urlunsplit
from urllib import quote
from django.conf import settings
from django.utils.http import is_safe_url
from django.http.request import validate_host
from django.core.urlresolvers import reverse, resolve
import requests
import logging

try:
    from ssl_pki.models import has_ssl_config
    from ssl_pki.views import pki_request
    from ssl_pki.utils import (
        protocol_relative_url,
        protocol_relative_to_scheme,
    )
except ImportError:
    has_ssl_config = None
    pki_request = None
    protocol_relative_url = None
    protocol_relative_to_scheme = None

logger = logging.getLogger(__name__)


def proxy(request):
    PROXY_ALLOWED_HOSTS = getattr(settings, 'PROXY_ALLOWED_HOSTS', ())

    host = None

    if 'geonode.geoserver' in settings.INSTALLED_APPS:
        from geonode.geoserver.helpers import ogc_server_settings
        hostname = (ogc_server_settings.hostname,) if ogc_server_settings else ()
        PROXY_ALLOWED_HOSTS += hostname
        host = ogc_server_settings.netloc

    if 'url' not in request.GET:
        return HttpResponse("The proxy service requires a URL-encoded URL as a parameter.",
                            status=400,
                            content_type="text/plain"
                            )

    raw_url = request.GET['url']
    url = urlsplit(raw_url)
    headers = {}

    # Fix up any possible non-absolute URLs that have no scheme, or even domain
    if ((callable(protocol_relative_url) and protocol_relative_url(raw_url))
            or not url.scheme):
        if url.netloc and callable(protocol_relative_to_scheme):
            # Fix up any '//' protocol relative URLs coming from JS map viewers
            # Use request.scheme to reference origin scheme context
            # Note: Can't use request.build_absolute_uri(raw_url) for this
            raw_url = protocol_relative_to_scheme(url.geturl(),
                                                  scheme=request.scheme)
            # logger.debug("protocol_relative_to_scheme = ".format(raw_url))
        else:
            raw_url = request.build_absolute_uri(raw_url)
            # logger.debug("build_absolute_uri = ".format(raw_url))
        url = urlsplit(raw_url)

    if not settings.DEBUG:
        if not (validate_host(url.hostname, PROXY_ALLOWED_HOSTS)
                or (callable(has_ssl_config)
                    and has_ssl_config(url.geturl()))):
            return HttpResponse(
                "DEBUG is set to False but the host of the path provided to "
                "the proxy service is not in the PROXY_ALLOWED_HOSTS setting "
                "or defined to use the proxy in SSL/PKI configurations.",
                status=403,
                content_type="text/plain"
            )

    if url.scheme.lower() == 'https' \
            and callable(has_ssl_config) and has_ssl_config(url.geturl()):
        # Adjust request to mock call to pki_request view
        # Merge queries
        pki_req_query = request.GET.copy()
        """django.http.QueryDict"""
        # Strip the url param from request query
        del pki_req_query['url']
        # Note: leave other query pairs passed to this view, e.g. access_token

        # Add any query from passed url param's URL
        url_query = url.query.strip()
        for k, v in parse_qsl(url_query, keep_blank_values=True):
            pki_req_query.appendlist(k, v)
        request.GET = pki_req_query
        request.META["QUERY_STRING"] = pki_req_query.urlencode()

        # pki_request view is restricted to local calls
        request.META["REMOTE_ADDR"] = '127.0.0.1'
        request.META["REMOTE_HOST"] = 'localhost'
        # TODO: Update HTTP_X_FORWARDED_FOR? See: api.views.get_client_ip()

        base_url = urlunsplit((None, url.netloc, url.path, None, None))\
            .replace('//', '', 1)
        # For pki_request view, resource_url has no URL scheme
        resource_url = quote(base_url)

        pki_path = reverse('pki_request',
                           kwargs={'resource_url': resource_url})
        # Reset view paths attributes
        request.path = request.path_info = pki_path
        request.META["PATH_INFO"] = pki_path
        request.resolver_match = resolve(pki_path)

        logger.debug("pki_req QueryDict: {0}".format(pki_req_query))
        # logger.debug("pki_req META: {0}".format(request.META))
        logger.debug("pki_req META['QUERY_STRING']: {0}"
                     .format(request.META["QUERY_STRING"]))
        logger.debug("Routing through pki proxy: {0}".format(resource_url))
        return pki_request(request, resource_url=resource_url)

    if settings.SESSION_COOKIE_NAME in request.COOKIES and is_safe_url(url=raw_url, host=host):
        headers["Cookie"] = request.META["HTTP_COOKIE"]

    if request.method in ("POST", "PUT") and "CONTENT_TYPE" in request.META:
        headers["Content-Type"] = request.META["CONTENT_TYPE"]

    http_client = requests.session()
    http_client.verify = True
    req_method = getattr(http_client, request.method.lower())
    resp = req_method(raw_url, headers=headers, data=request.body)

    if 'Content-Type' in resp.headers:
        content_type = resp.headers['Content-Type']
    else:
        content_type = 'text/plain'

    # If we get a redirect, let's add a useful message.
    if resp.status_code in (301, 302, 303, 307):
        response = HttpResponse(('This proxy does not support redirects. The server in "%s" '
                                 'asked for a redirect to "%s"' % (raw_url, resp.headers['Location'])),
                                status=resp.status_code,
                                content_type=content_type
                                )

        response['Location'] = resp.headers['Location']
    else:
        response = HttpResponse(
            resp.content,
            status=resp.status_code,
            content_type=content_type
        )

    return response
