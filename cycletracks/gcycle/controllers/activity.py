from django.http import *
from django.conf import settings

from django.shortcuts import render_to_response
from django.template import loader, Context

from django.utils import simplejson
from django.contrib.auth import decorators as auth_decorators

from google.appengine.api import datastore_errors
from google.appengine.api import memcache
from google.appengine.api import urlfetch

import urllib
import logging
import datetime

from gcycle.models import *
from gcycle.templatetags.extra_filters import *
from gcycle.lib.memoized import *

def require_valid_activity(f):
  def wrapper(request, *args, **kw):
    a = Activity.get_by_id(int(args[0]))
    if a is None:
      raise Http404
    return f(request, a)

  return wrapper


@auth_decorators.login_required
def index(request, sorting=None, user=None):
  if user is None:
    user = request.user
  else:
    user = User.get(user)

  if sorting is None: sorting = 'start_time'
  activity_query = Activity.all()
  activity_query.filter('user = ', user)
  activity_query.order('-%s' % sorting)
  activities_exist = activity_query.count(1)
  return render_to_response(
    'dashboard.html',
    {'user_activities' : activity_query,
     'num_activities' :activities_exist,
     'user_totals': user.get_profile(),
     'user' : user,
    })

@auth_decorators.login_required
def tag(request, tag):
  """Like the index action but only shows activities with a certain tag"""
  acts = Activity.all()
  acts.filter('user =', request.user)
  acts.filter('tags =', tag)
  acts.order('-start_time')

  user_activities = acts
  return render_to_response(
      'activity/tag.html',
      { 'user_activities': user_activities,
        'tag': tag,
        'user': request.user})


@require_valid_activity
def activity_kml(request, activity):
  """Convert the activity in to a kml file

  Args:
  - request: standard django request object
  - activity_id: Activity key as a string

  Returns:
  - rendered kml file
  """
  return HttpResponse(
      loader.render_to_string('activity/kml.html',
        { 'user' : activity.user,
          'activity' : activity}),
      mimetype='application/vnd.google-earth.kml+xml'
      )


def kml_location(request, activity):
  """Helper function to generate the link to an Activities kml url"""
  return ("http://%s/activity/kml/%s" % (
    request.META['HTTP_HOST'], activity.key().id()))

def show_cache_key(activity, use_imperial):
  return '%s_%s' % (activity.key(), use_imperial)

def show_activity(request, activity):
  use_imperial = activity.user.get_profile().use_imperial
  if not request.user.is_anonymous():
    use_imperial = request.user.get_profile().use_imperial

  activity_stats = memcache.get(show_cache_key(activity, use_imperial))
  if settings.DEBUG: activity_stats = None

  if activity_stats is None:
    activity_stats = {
      'activity' : activity,
      'kml_location' : kml_location(request, activity),
      'use_imperial' : use_imperial,
      'pts': simplejson.dumps(activity.encoded_points),
      'levs' : simplejson.dumps(activity.encoded_levels),
    }
  return render_to_response('activity/show.html', activity_stats)


# So people don't have to login to see a public activity.
@require_valid_activity
def public(request, activity):
  if not activity.public:
    return non_public_activity()

  return show_activity(request, activity)


@auth_decorators.login_required
@require_valid_activity
def show(request, activity):
  if (activity.safeuser != request.user and not activity.public
      and not request.user.is_superuser):
    return non_public_activity()

  return show_activity(request, activity)


@require_valid_activity
def source(request, activity):
  if (activity.safeuser != request.user and not activity.public
      and not request.user.is_superuser):
    return non_public_activity()

  sourcedata = activity.sourcedatafile_set.get()
  if sourcedata is None:
    raise Http404("This activity doesn't have a source file")
  return HttpResponse(
      activity.sourcedatafile_set[0].data,
      mimetype='text/plain',
  )


@memoized
def data_cache_key(activity):
  return '%s_%s_data' % (
      activity.key(),
      activity.user.get_profile().use_imperial
      )

def non_public_activity():
  return HttpResponseForbidden(
      "You are not allowed to see this activity. The activity doesn't"
      "belong to you and the owner hasn't made it public."
  )



@require_valid_activity
def data(request, activity):
  """Convert activity datasets into a text file usable by timeplot:
  date,altitude,speed,cadence,distance,bpm

  Requires a valid activity_id.
  """
  if (activity.safeuser != request.user and not activity.public
      and not request.user.is_superuser):
    return non_public_activity()

  activity_data = memcache.get(data_cache_key(activity))
  if settings.DEBUG: activity_data = None

  if activity_data is None:
    use_imperial = activity.user.get_profile().use_imperial
    data = []
    data = map(None, *[
        activity.time_list,
        activity.altitude_list,
        activity.speed_list,
        activity.cadence_list,
        activity.distance_list,
        activity.bpm_list]
        )
    activity_data = []
    st = activity.start_time + datetime.timedelta(
        hours = activity.user.get_profile().tzoffset
        )

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

  if not memcache.set(data_cache_key(activity), activity_data, 60 * 60):
    logging.error("Memcache set failed for %s" % data_cache_key(activity))


  return HttpResponse(
      loader.render_to_string('activity/data.html',
        { 'data' : "\n".join(activity_data)}),
      mimetype='text/plain'
      )


UPDATEABLE_ACTIVITY_ATTRIBUTES = ['comment', 'name', 'public', 'tags']

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

    activity = Activity.get_by_id(int(activity_id))
    if activity is None:
      raise Http404

    if activity.user != request.user:
      return HttpResponseForbidden('')

    if activity_attribute in UPDATEABLE_ACTIVITY_ATTRIBUTES:
      if getattr(activity, activity_attribute) != activity_value:
        setattr(activity, activity_attribute, activity_value)
        activity.put()
      return HttpResponse(activity_value)
  except Exception, e:
    return HttpResponse('Error: %s' % e)


@auth_decorators.login_required
def delete(request):
  if request.method == 'POST':
    if 'activity_id' not in request.POST:
      return HttpResponseNotFound('No activity id given')
    activity_id = request.POST['activity_id']
    a = Activity.get_by_id(int(activity_id))
    if a is None:
      raise Http404
    if request.user != a.user:
      return HttpResponseForbidden('')

    a.delete()
    if not memcache.delete(str(a.key())):
      logging.error("Memcache delete failed.")

    return HttpResponse('')
  else:
    return HttpResponse('Must use POST')
