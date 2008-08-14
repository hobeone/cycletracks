from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
import django.utils.safestring
from gcycle.models import Activity, Lap
from gcycle import views
from gcycle.lib import glineenc

from google.appengine.api import datastore_errors
from google.appengine.api import memcache
import logging
from django.utils import simplejson

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


def graph(request, activity):
  user = views.get_user()
  a = Activity.get(activity)
  return render_to_response('activity/graph.html',
      {'activity' : a,
       'user' : user,
       'bpm' : ','.join([str(b) for b in process_data(a.bpm_list())]),
       'cadence' : ','.join([str(b) for b in process_data(a.cadence_list())]),
       'speed' : process_data(a.speed_list()),
       'altitude' : ','.join([str(b) for b in process_data(a.altitude_list())]),})

def show(request, activity):
  user = views.get_user()
  try:
    a = Activity.get(activity)
  except datastore_errors.BadKeyError, e:
    return render_to_response('error.html',
        {'error': "That activity doesn't exist."})

  if a.user != user and not a.public:
    return render_to_response('error.html',
        {'error': "You are not allowed to see this activity. %s" % a.public})
  else:
    activity_stats = memcache.get(str(a.key()))
    if activity_stats is None:
      points = []
      for lap in a.lap_set:
        points.extend(lap.geo_points.split('\n'))
      newp = [ (float(p.split(',')[0]), float(p.split(',')[1])) for p in points]
      minlat, maxlat = 90,-90
      minlong, maxlong = 180,-180
      for pt in newp:
        lat,long = pt[0],pt[1]
        if lat > maxlat: maxlat = lat
        if lat < minlat: minlat = lat
        if long > maxlong: maxlong = long
        if long < minlong: minlong = long
      sw = (minlat, minlong)
      ne = (maxlat, maxlong)

      pts, levs = glineenc.encode_pairs(newp)
      tlist = a.time_list()
      times = [
          (0, tlist[0]),
          (250, tlist[int(len(tlist) / 2)]),
          (500, tlist[-1]),
          ]
      activity_stats = {'activity' : a,
           'user' : user,
           'bpm' : process_data(a.bpm_list()),
           'cadence' : process_data(a.cadence_list()),
           'speed' : process_data(a.speed_list()),
           'altitude' : process_data(a.altitude_list()),
           'pts': simplejson.dumps(pts),
           'levs' : simplejson.dumps(levs),
           'sw' : '%s,%s' % (sw[0],sw[1]),
           'ne' : '%s,%s' % (ne[0],ne[1]),
           'times': times,
           'start_lat_lng' : points[0],
           'mid_lat_lng' : points[int(len(points) / 2.0)],
           'end_lat_lng' : points[-2],
           }
      if not memcache.set(str(a.key()), activity_stats, 60 * 60):
        logging.error("Memcache set failed for %s." % str(a.key()))
    else:
      logging.debug('Got cached version of activity')

    return render_to_response('activity/show.html', activity_stats)


VALID_ACTIVITY_ATTRIBUTES = ['comment', 'name', 'public']

def update(request):
  try:
    user = views.get_user()
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
    if activity.user != user:
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
