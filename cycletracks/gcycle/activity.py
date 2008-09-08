from django.http import *
from django.conf import settings

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
from gcycle import views
from gcycle.models import *

def rm3gen(valuelist):
  """Given a list return a list of mean values based on a sliding 3 value window
  based on this which i knicked from the tubes:
  http://mail.python.org/pipermail/python-list/2002-September/163580.html

  Args:
  - valuelist: list of integers or floats

  Returns:
  - yields() each mean as an integer
  """
  temp = zip(valuelist[:-2], valuelist[1:-1], valuelist[2:])
  for x in temp:
    yield (int(sorted(x)[1]))


def downsample(items, timepoints, factor=10):
  """Crappy downsample by averaging factor items at a time.

  Args:
  - items: list to downsample, items must be summable
  - timepoints: list of times corresponding to each item
  - factor: factor to reduce the items by

  Returns:
  - list of downsampled items, and downsampled times
  """
  if len(items) != len(timepoints):
    logging.error("items and times are different lengths")

  window_start = 0
  samp = []
  times = []
  if factor < 1: factor = 1
  while window_start < len(items):
    samp.append(
        int(
          sum(items[window_start:window_start+factor])
            /
          float(factor)
        )
    )
    times.append(timepoints[window_start])
    window_start += factor

  return samp, times

def process_data_with_time(data, times):
  """Prepares data from an activity to be shown by the javascript graphing libs.

  Args:
  - data: list of datapoints
  - times: corresponding list of times

  Returns:
  - javascript 2d array as a string:  [time, datapoint], ...
  """
  index = 0
  factor = int(len(data) / 500.0)
  sampled_data, sampled_times = downsample(data,times,factor)
  export_data = []
  for i in rm3gen(sampled_data):
    export_data.append('[%s,%s]' % (sampled_times[index], i))
    index += 1

  return ','.join(export_data)


def activity_kml(request, activity_id):
  """Convert the activity in to a kml file

  Args:
  - request: standard django request object
  - activity_id: Activity key as a string

  Returns:
  - rendered kml file
  """
  a = Activity.get(activity_id)
  return HttpResponse(
      render_to_string('activity/kml.html',
        { 'points' : a.to_kml,
          'user' : a.user,
          'activity' : a}),
      mimetype='application/vnd.google-earth.kml+xml'
      )


def kml_location(request, activity):
  """Helper function to generate the link to an Activities kml url"""
  return ("http://%s/activity/kml/%s" % (request.META['HTTP_HOST'], activity.str_key))


def show_activity(request, a):
  activity_stats = memcache.get(a.str_key)
  if settings.DEBUG: activity_stats = None
  if activity_stats is None:
    activity_stats = {
      'activity' : a,
      'user' : a.user,
      'bpm' : process_data_with_time(a.bpm_list, a.time_list),
      'cadence' : process_data_with_time(a.cadence_list, a.time_list),
      'speed' : process_data_with_time(a.speed_list, a.time_list),
      'altitude' : process_data_with_time(a.altitude_list, a.time_list),
      'distance' : process_data_with_time(a.distance_list, a.time_list),
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
        (tlist[-1] / 2, tlist[-1] / 2),
        (activity_stats['speed'].split('],[')[-1].split(',')[0], tlist[-1]),
        ]
    activity_stats['times'] = times
    if not memcache.set(a.str_key, activity_stats, 60 * 120):
      logging.error("Memcache set failed for %s." % a.str_key)
  else:
    logging.debug('Got cached version of activity')

  return render_to_response('activity/show.html', activity_stats)


# So people don't have to login to see a public activity.
def public(request, activity):
  a = Activity.get(activity)
  if a is None:
    return render_to_response('error.html',
        {'error': "That activity doesn't exist."})


  if(not a.public):
    return render_to_response('error.html',
      {'error': "You are not allowed to see this activity.  The activity doesn't belong to you and the owner hasn't made it public."})

  return show_activity(request, a)


@auth_decorators.login_required
def show(request, activity):
  a = Activity.get(activity)
  if a is None:
    return render_to_response('error.html',
        {'error': "That activity doesn't exist."})

  if (a.safeuser != request.user and not a.public
      and not request.user.is_superuser):
    return render_to_response('error.html',
        {'error': "You are not allowed to see this activity.  The activity doesn't belong to you and the owner hasn't made it public."})

  return show_activity(request, a)


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
        if not memcache.delete(views.dashboard_cache_key(request.user)):
          logging.error("Memcache delete failed.")
      return HttpResponse(activity_value)
  except Exception, e:
    return HttpResponse(e)

@auth_decorators.login_required
def delete(request):
  if request.method == 'POST':
      activity_id = request.POST['activity_id']
      a = Activity.get(activity_id)
      if a is None:
        return HttpResponseNotFound(
            "That activity doesn't exist")
      if request.user != a.user:
        return HttpResponseForbidden(
            'You are not allowed to delete this activity')

      a.safe_delete()
      if not memcache.delete(str(a.key())):
        logging.error("Memcache delete failed.")
      if not memcache.delete(views.dashboard_cache_key(request.user)):
        logging.error("Memcache delete failed.")

      return HttpResponse('')
  else:
    return HttpResponse('Must use POST')
