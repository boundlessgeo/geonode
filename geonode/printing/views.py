from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import Context
from django.template import Template
from geonode.printing.models import PrintTemplate


def template_view(request, templateid):
    """interpolate the template with the given id"""

    template_obj = get_object_or_404(PrintTemplate, pk=templateid)
    template = Template(template_obj.contents)
    context = Context(request.GET)
    rendered = template.render(context)
    return HttpResponse(rendered, content_type="text/html")
