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

from actstream.models import Action
from django.views.generic import ListView
from guardian.shortcuts import get_objects_for_user
import logging

logger = logging.getLogger(__name__)

def get_filter_ids(user):
    filter_set = get_objects_for_user(
        user,
        'base.view_resourcebase'
    )
    return map(str, filter_set.values_list('id', flat=True))

class RecentActivity(ListView):
    """
    Returns recent public activity.
    """
    context_object_name = 'action_list'
    queryset = Action.objects.filter(public=True)[:15]
    template_name = 'social/activity_list.html'


    def get_queryset(self):
        self.filter_set_ids = get_filter_ids(self.request.user)
        return Action.objects.filter(
            action_object_object_id__in=self.filter_set_ids
        )


    def get_context_data(self, *args, **kwargs):
        context = super(ListView, self).get_context_data(*args, **kwargs)
        context['action_list_layers'] = Action.objects.filter(
            action_object_object_id__in=self.filter_set_ids,
            public=True,
            action_object_content_type__model='layer')[:15]
        context['action_list_maps'] = Action.objects.filter(
            action_object_object_id__in=self.filter_set_ids,
            public=True,
            action_object_content_type__model='map')[:15]
        context['action_list_comments'] = Action.objects.filter(
            action_object_object_id__in=self.filter_set_ids,
            public=True,
            action_object_content_type__model='comment')[:15]
        return context


class UserActivity(ListView):
    """
    Returns recent user activity.
    """
    context_object_name = 'action_list'
    template_name = 'actstream/actor.html'

    def get_queryset(self):
        # There's no generic foreign key for 'actor', so can't filter directly
        # Hence the code below is essentially applying the filter afterwards

        self.filter_set_ids = get_filter_ids(self.request.user)
        actions = Action.objects.filter(
            public=True,
            action_object_object_id__in=self.filter_set_ids
        )
        return [x for x in actions[:15]
                if x.actor.username == self.kwargs['actor']]

    def get_context_data(self, *args, **kwargs):
        context = super(ListView, self).get_context_data(*args, **kwargs)
        context['actor'] = self.kwargs['actor']
        return context
