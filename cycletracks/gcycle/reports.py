from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import render_to_response
from django.template.loader import render_to_string

from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.contrib.auth import decorators as auth_decorators

from google.appengine.api import datastore_errors
from google.appengine.api import memcache

import logging
import datetime
from gcycle.models import *

def group_by_attr(activities, groupby):
  group = {}
  for a in activities:
    key = groupby(a)
    if key not in group:
      group[key] = []
    group[key].append(a)

  return group

def next_month(dtime):
  next_month = dtime.month + 1
  next_year = dtime.year
  if dtime.month == 12:
    next_year += 1
    next_month = 1

  return datetime.date(year=next_year, month=next_month, day=dtime.day)

def sum_by_buckets(activities, buckets, timegroup):
  acts = group_by_attr(activities, timegroup)

  data = SortedDict()
  for bucket in buckets:
    if bucket in acts.keys():
      data[bucket] = acts[bucket][0]
      for a in acts[bucket][1:]:
        data[bucket] += a
    else:
      data[bucket] = None

  return data


@auth_decorators.login_required
def report(request, group_by):
  if not group_by: group_by = "week"
  acts = Activity.all().order('start_time')
  acts.ancestor(request.user)
  acts = acts.fetch(1000)

  firstdate = datetime.date(
      year=acts[0].start_time.year,
      month=acts[0].start_time.month,
      day=acts[0].start_time.day)

  lastdate = datetime.date(
      year=acts[-1].start_time.year,
      month=acts[-1].start_time.month,
      day=acts[-1].start_time.day)

  if group_by == 'day':
    timedelta = datetime.timedelta(days=1)
    timegroup = lambda a: datetime.date(a.start_time.year,a.start_time.month,a.start_time.day)
    tickformat = "%b %d %y"
    firstdate = firstdate - (firstdate - firstdate.replace(day=firstdate.day - firstdate.weekday() + 1))

  elif group_by == 'month':
    tickformat = "%b %Y"
    firstdate = firstdate.replace(day=1)
    lastdate = lastdate.replace(day=1)
    timegroup = lambda a: datetime.date(a.start_time.year,a.start_time.month,1)

  else:
    group_by = 'week'
    tickformat = "%b %d"
    firstdate = firstdate - (firstdate - firstdate.replace(day=firstdate.day - firstdate.weekday() + 1))
    lastdate = lastdate.replace(day=1)
    timedelta = datetime.timedelta(days=7)
    timegroup = lambda a: datetime.date(a.start_time.year,a.start_time.month,a.start_time.day)

  buckets = [firstdate]
  while buckets[-1] < lastdate:
    if group_by in ['day','week']:
      buckets.append(buckets[-1] + timedelta)
    else:
      pdate = buckets[-1]
      buckets.append(next_month(buckets[-1]))

  data = sum_by_buckets(acts, buckets, timegroup)
  return render_to_response('report.html',
      {'data' : data,
       'tickformat' : tickformat,
       'group_by' : group_by,
       'user':  request.user}
  )
