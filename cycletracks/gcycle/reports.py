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
    js_timestamp = int(bucket[0].strftime('%s')) * 1000
    data[js_timestamp] = None
    for act_date in acts.keys():
      if act_date >= bucket[0] and act_date < bucket[1]:
        print bucket[0].ctime()
        if data[js_timestamp] is None:
          data[js_timestamp] = acts[act_date][0]
          for act in acts[act_date][1:]:
            data[js_timestamp] += act
        else:
          for act in acts[act_date]:
            data[js_timestamp] += act

  return data

def getBucketEnd(start, bucketsize):
  bucketend = None
  if bucketsize == 'day':
    bucketend = start + datetime.timedelta(days=1)
  elif bucketsize == 'week':
    bucketend = start + datetime.timedelta(days=7)
  else:
    bucketend = next_month(start)
  return bucketend


def createBuckets(startdate, lastdate, bucketsize):
  bucket_start = startdate
  bucket_end = getBucketEnd(startdate, bucketsize)
  buckets = [ [bucket_start, bucket_end] ]
  while buckets[-1][1] < lastdate:
    buckets.append([ buckets[-1][1], getBucketEnd(buckets[-1][1], bucketsize) ])

  return buckets


@auth_decorators.login_required
def report(request, group_by):
  if not group_by: group_by = "week"
  acts = Activity.all().order('start_time')
  acts.ancestor(request.user)
  acts = acts.fetch(1000)


  if not acts:
    return render_to_response('report.html', {
      'data': None,
      'user': request.user
      })

  else:
    firstdate = datetime.date(
        year=acts[0].start_time.year,
        month=acts[0].start_time.month,
        day=acts[0].start_time.day)

    lastdate = datetime.date(
        year=acts[-1].start_time.year,
        month=acts[-1].start_time.month,
        day=acts[-1].start_time.day)

    if group_by == 'day':
      barwidth = 24 * 60 * 60 * 1000
      timegroup = lambda a: datetime.date(a.start_time.year,a.start_time.month,a.start_time.day)
      tickformat = "%b %d %y"
      ticksize = '[1, "day"]'

    elif group_by == 'month':
      tickformat = "%b %y"
      ticksize = '[1, "month"]'
      barwidth = 24 * 60 * 60 * 1000 * 30
      firstdate = firstdate.replace(day=1)
      lastdate = lastdate.replace(day=1)
      timegroup = lambda a: datetime.date(a.start_time.year,a.start_time.month,1)

    else:
      group_by = 'week'
      tickformat = "%b %d"
      ticksize = '[7, "day"]'
      barwidth = 24 * 60 * 60 * 1000 * 7
      firstdate = firstdate - datetime.timedelta(days=firstdate.weekday())
      timegroup = lambda a: datetime.date(a.start_time.year,a.start_time.month,a.start_time.day)

    buckets = createBuckets(firstdate, lastdate, group_by)
    data = sum_by_buckets(acts, buckets, timegroup)

    return render_to_response('report.html',
        {'data' : data,
         'barwidth': barwidth,
         'tickformat' : tickformat,
         'ticksize' : ticksize,
         'group_by' : group_by,
         'user':  request.user}
  )
