from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from gcycle.models import Activity, Lap
from gcycle import views

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

def test_js_graph(request, activity):
  user = views.get_user()
  a = Activity.get(activity)
  bpm = a.bpm_list()

  data = []
  index = 0
  for i in bpm:
    data.append('{x:%s, y:%s}' % (index, i))
    index += 1

  data = '[%s]' % ','.join(data)
  return render_to_response('activity/graphtest.html',
      {'data' : a.bpm_list()})

def process_data(data):
  return rm3(downsample(data, int(len(data) / 500.0)))

def show(request, activity):
  user = views.get_user()
  a = Activity.get(activity)
  points = []
  for lap in a.lap_set:
    points.extend(lap.geo_points.split('\n'))
  return render_to_response('activity/show.html',
      {'activity' : a,
       'user' : user,
       'bpm' : process_data(a.bpm_list()),
       'cadence' : process_data(a.cadence_list()),
       'speed' : process_data(a.speed_list()),
       'altitude' : process_data(a.altitude_list()),
       'points' : points[:-2],
       'centerpoint' : points[int(len(points) / 2.0)]})
