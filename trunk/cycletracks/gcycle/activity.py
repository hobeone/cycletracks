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
  a = Activity.get(activity)
  points = []
  for lap in a.lap_set:
    points.extend(lap.geo_points.split('\n'))
  tlist = a.time_list()
  times = [
      (0, tlist[0]),
      (250, tlist[int(len(tlist) / 2)]),
      (500, tlist[-1]),
      ]
  return render_to_response('activity/show.html',
      {'activity' : a,
       'user' : user,
       'bpm' : process_data(a.bpm_list()),
       'cadence' : process_data(a.cadence_list()),
       'speed' : process_data(a.speed_list()),
       'altitude' : process_data(a.altitude_list()),
       'points': points,
       'times': times,
       'start_lat_lng' : points[0],
       'end_lat_lng' : points[-2],
       'centerpoint' : points[int(len(points) / 2.0)]
       })


VALID_ACTIVITY_ATTRIBUTES = ['comment', 'name', 'public']

def update(request):
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
  if activity_attribute in VALID_ACTIVITY_ATTRIBUTES:
    if getattr(activity, activity_attribute) != activity_value:
      setattr(activity, activity_attribute, activity_value)
      activity.put()
    return HttpResponse(activity_value)
