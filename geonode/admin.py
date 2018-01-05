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

from django.contrib import admin
from django.utils.translation import ugettext_lazy
from django.conf import settings

# The text to put at the top of each admin page, as an <h1> (a string).
# By default, this is "Django administration".
admin.site.site_title = '%s %s' % (settings.SITENAME, ugettext_lazy('Administration'))

# The text to put at the end of each admin pages title.
# By default, this is "Django site admin".
admin.site.site_header = '%s %s' % (settings.SITENAME, ugettext_lazy('Administration'))

# The text to put at the top of the admin index page (a string).
# By default, this is "Site administration".
admin.site.index_title = '%s %s' % (settings.SITENAME, ugettext_lazy('Administration'))


