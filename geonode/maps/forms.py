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

from geonode.maps.models import Map

from geonode.base.forms import ResourceBaseForm
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class MapForm(ResourceBaseForm):

    def clean(self):
        cleaned_data = super(MapForm, self).clean()

        if not cleaned_data['featuredurl'].isalnum():
            self.add_error('featuredurl',
                           _('Featured url should be an alphanumeric string'))
        if not cleaned_data['urlsuffix'].isalnum():
            self.add_error('urlsuffix',
                           _('Url suffix should be an alphanumeric string'))

    class Meta(ResourceBaseForm.Meta):
        model = Map
        exclude = ResourceBaseForm.Meta.exclude + (
            'zoom',
            'projection',
            'center_x',
            'center_y',
            'tkeywords',
        )
        if settings.MAPLOOM_ENABLED is False:
            exclude = exclude + ('refresh_interval',)
