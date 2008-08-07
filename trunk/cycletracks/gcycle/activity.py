from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from gcycle.models import Activity, Lap
from gcycle import views

def show(request, activity):
  user = views.get_user()
  a = Activity.get(activity)
  points = []
  for lap in a.lap_set:
    points.extend(lap.geo_points.split('\n'))
  return render_to_response('activity/show.html',
      {'activity' : a,
       'user' : user,
       'points' : points[:-2],
       'centerpoint' : points[int(len(points) / 2.0)]})
