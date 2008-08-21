from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import render_to_response
from django.template.loader import render_to_string

from django.utils import simplejson
from django.contrib.auth import decorators as auth_decorators

from google.appengine.api import datastore_errors
from google.appengine.api import memcache

import logging

from gcycle.models import *

def group_by_attr(activities, groupby):
  group = {}
  for a in activities:
    key = groupby(a)
    if key not in group:
      group[key] = []
    group[key].append(a)

  return group

def sum_grouped(grouped):
  added = {}
  for key,acts in grouped.iteritems():
    added[key] = acts[0]
    for a in acts[1:]:
      added[key] += a

  return added

# [ {ylabels, bpm, cadence, speed, ....} ]


@auth_decorators.login_required
def report(request, group_by):
  if not group_by: group_by = "week"
  acts = Activity.all().order('start_time')
  acts.ancestor(request.user)
  timegroup = '%Y%U'

  series = 'Average Heart Rate (BPM)'
  if group_by == 'month':
    timegroup = '%Y%m'
  acts = group_by_attr(acts, lambda a: int(a.start_time.strftime(timegroup)))
  acts = sum_grouped(acts)

  for i in xrange(min(acts.keys()), max(acts.keys())):
    if not i in acts:
      acts[i] = None

  data = {}
  data['ylabels'] = acts.keys()
  for i in ['average_bpm', 'average_cadence', 'average_speed', 'total_time']:
    data[i] = [int(getattr(v,i,0)) for k,v in acts.iteritems()]

  return render_to_response('report.html',
      {'data' : data,
       'series' : series,
       'group_by' : group_by,
       'user':  request.user}
  )
