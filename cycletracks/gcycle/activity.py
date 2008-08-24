from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import render_to_response
from django.template.loader import render_to_string

from django.utils import simplejson
from django.contrib.auth import decorators as auth_decorators

from google.appengine.api import datastore_errors
from google.appengine.api import memcache
from google.appengine.api import urlfetch
import urllib
import django.utils.simplejson

import logging

from gcycle.models import *

def rm3(s):
  """knicked from the tubes:
  http://mail.python.org/pipermail/python-list/2002-September/163580.html"""
  temp = map(lambda x,y,z:[x,y,z], s[:-2], s[1:-1], s[2:])
  temp2 = []
  for x in temp:
    x.sort()
    temp2.append(int(x[1]))
  return temp2


def downsample(items, factor=10):
  """Crappy downsample by averaging factor items at a time"""
  window_start = 0
  samp = []
  if factor < 1: factor = 1
  while window_start < len(items):
    samp.append(
        int(
          sum(items[window_start:window_start+factor])
            /
          float(factor)
        )
    )
    window_start += factor

  return samp

def process_data(data):
  data = rm3(downsample(data, int(len(data) / 500.0)))
  index = 0
  export_data = []
  for i in data:
    export_data.append('[%s,%s]' % (index, i))
    index += 1

  return ','.join(export_data)


@auth_decorators.login_required
def graph(request, activity):
  a = Activity.get(activity)
  return render_to_response('activity/graph.html',
      {'activity' : a,
       'user' : request.user,
       'bpm' : process_data(a.bpm_list),
       'cadence' : process_data(a.cadence_list),
       'speed' : process_data(a.speed_list),
       'altitude' : process_data(a.altitude_list),
      })


def activity_kml(request, activity_id):
  a = Activity.get(activity_id)
  return HttpResponse(
      render_to_string('activity/kml.html',
        { 'points' : a.to_kml,
          'user' : a.user,
          'activity' : a}),
      mimetype='application/vnd.google-earth.kml+xml'
      )

def kml_location(request, activity):
  return ("http://%s/activity/kml/%s" % (request.META['HTTP_HOST'], activity.str_key))


@auth_decorators.login_required
def show(request, activity):
  a = Activity.get(activity)
  if a is None:
    return render_to_response('error.html',
        {'error': "That activity doesn't exist."})

  if a.safeuser != request.user and not a.public:
    return render_to_response('error.html',
        {'error': "You are not allowed to see this activity."})
  else:
    activity_stats = memcache.get(a.str_key)
    if activity_stats is None:
      activity_stats = {
        'activity' : a,
        'user' : request.user,
        'bpm' : process_data(a.bpm_list),
        'cadence' : process_data(a.cadence_list),
        'speed' : process_data(a.speed_list),
        'altitude' : process_data(a.altitude_list),
        'pts': simplejson.dumps(a.encoded_points),
        'levs' : simplejson.dumps(a.encoded_levels),
        'sw' : a.sw_point,
        'ne' : a.ne_point,
        'start_lat_lng' : a.start_point,
        'mid_lat_lng' : a.mid_point,
        'end_lat_lng' : a.end_point,
        'kml_location' : kml_location(request, a),
      }
      tlist = a.time_list
      times = [
          (0, tlist[0]),
          ((len(activity_stats['bpm'].split(',')) - 1) / 4, tlist[len(tlist) / 2]),
          ((len(activity_stats['bpm'].split(',')) - 1) / 2, tlist[-1]),
          ]
      activity_stats['times'] = times
      if not memcache.set(a.str_key, activity_stats, 60 * 120):
        logging.error("Memcache set failed for %s." % a.str_key)
    else:
      logging.debug('Got cached version of activity')
    activity_stats['user'] = request.user

  return render_to_response('activity/show.html', activity_stats)


VALID_ACTIVITY_ATTRIBUTES = ['comment', 'name', 'public']

@auth_decorators.login_required
def update(request):
  try:
    activity_id = request.POST['activity_id']
    activity_attribute = request.POST['attribute']
    activity_value = request.POST['value']

    # LAME
    if activity_attribute == 'public':
      if activity_value == 'False':
        activity_value = False
      else:
        activity_value = True

    activity = Activity.get(activity_id)
    if activity.user != request.user:
      return render_to_response('error.html',
        {'error': "You are not allowed to edit this activity"})

    if activity_attribute in VALID_ACTIVITY_ATTRIBUTES:
      if getattr(activity, activity_attribute) != activity_value:
        setattr(activity, activity_attribute, activity_value)
        activity.put()
        if not memcache.delete(str(activity.key())):
          logging.error("Memcache delete failed.")
      return HttpResponse(activity_value)
  except Exception, e:
    return HttpResponse(e)

@auth_decorators.login_required
def delete(request):
  if request.method == 'POST':
    try:
      activity_id = request.POST['activity_id']
      a = Activity.get(activity_id)
      if request.user != a.user:
        return HttpResponseServerError(
            'You are not allowed to delete this activity')

      a.safe_delete()
      return HttpResponse('')
    except Exception, e:
      return HttpResponseServerError(e)
  else:
    return HttpResponse('Must use POST')
