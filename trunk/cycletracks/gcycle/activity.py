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
import datetime
from gcycle import views
from gcycle.models import *
from gcycle.templatetags.extra_filters import *

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
  return ("http://%s/activity/kml/%s" % (request.META['HTTP_HOST'], activity.key()))


def show_activity(request, a):
  activity_stats = {
    'activity' : a,
    'user' : a.user,
    'pts': simplejson.dumps(a.encoded_points),
    'levs' : simplejson.dumps(a.encoded_levels),
    'sw' : a.sw_point,
    'ne' : a.ne_point,
    'start_lat_lng' : a.start_point,
    'mid_lat_lng' : a.mid_point,
    'end_lat_lng' : a.end_point,
    'kml_location' : kml_location(request, a),
  }
  return render_to_response('activity/show.html', activity_stats)


# So people don't have to login to see a public activity.
def public(request, activity):
  a = Activity.get(activity)
  if a is None:
    return render_to_response('error.html',
        {'error': "That activity doesn't exist."})

  if(not a.public):
    return render_to_response('error.html',
      {'error': "You are not allowed to see this activity. The activity doesn't belong to you and the owner hasn't made it public."})

  return show_activity(request, a)


def data(request, activity_id):
  """Convert activity datasets into a text file usable by timeplot:
  date,altitude,speed,cadence,distance,bpm

  Requires a valid activity_id.
  """
  activity = Activity.get(activity_id)
  if activity is None:
    return render_to_response('error.html',
        {'error': "That activity doesn't exist."})
  if (activity.safeuser != request.user and not activity.public
      and not request.user.is_superuser):
    return render_to_response('error.html',
        {'error': ("You are not allowed to see this activity. The activity doesn't belong to you and the owner hasn't made it public.")})

  activity_data = memcache.get('%s_data' % activity.key())
  if settings.DEBUG: activity_data = None

  if activity_data is None:
    use_imperial = activity.user.get_profile().use_imperial
    data = []
    data = zip(activity.time_list, activity.altitude_list,
        activity.speed_list, activity.cadence_list,
        activity.distance_list, activity.bpm_list)
    activity_data = []
    st = activity.start_time + datetime.timedelta(hours=activity.user.get_profile().tzoffset)

    for t,a,s,c,d,b in data:
      activity_data.append('%s,%s,%s,%s,%s,%s' % (
        (st + datetime.timedelta(seconds=t)).isoformat(),
        meters_or_feet(a,use_imperial),
        kph_to_prefered_speed(s,use_imperial),
        c,
        meters_to_prefered_distance(d,use_imperial),
        b
        )
      )

  if not memcache.set('%s_data' % activity.key(), activity_data, 60 * 60):
    logging.error("Memcache set failed for %s_data." % activity.key())


  return HttpResponse(
      render_to_string('activity/data.html',
        { 'data' : "\n".join(activity_data)}),
      mimetype='text/plain'
      )


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
    activity_value = request.POST['update_value']

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
    return HttpResponse('Error: %s' % e)


@auth_decorators.login_required
def delete(request):
  if request.method == 'POST':
    if 'activity_id' not in request.POST:
      return HttpResponseNotFound('No activity id given')
    activity_id = request.POST['activity_id']
    a = Activity.get(activity_id)
    if a is None:
      return HttpResponseNotFound(
          "That activity doesn't exist")
    if request.user != a.user:
      return HttpResponseForbidden(
          'You are not allowed to delete this activity')

    a.delete()
    if not memcache.delete(str(a.key())):
      logging.error("Memcache delete failed.")
    if not memcache.delete(views.dashboard_cache_key(request.user)):
      logging.error("Memcache delete failed.")

    return HttpResponse('')
  else:
    return HttpResponse('Must use POST')
