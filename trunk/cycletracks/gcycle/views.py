from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django import forms

from google.appengine.api import users

from gcycle import models
from gcycle import pytcx
from gcycle import OpenFlashChart

from google.appengine.ext import db

import sys,os,glob
import xml.etree.cElementTree as ET
import datetime

def get_user():
  gaia_user = users.get_current_user()
  return models.User.get_or_insert(gaia_user.email(), user = gaia_user)

def chart(request):
  return render_to_response('chart.html')


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

def chart_data(data_list, label, units, smooth_data=True, max_points=500.0):
  g = OpenFlashChart.graph()
  g.title(label,
          '{color: #999999; font-size: 12; text-align: center}' );
  g.bg_colour = '#ffffff'

  data = data_list
  if smooth_data:
    data = data_list
    smooth_factor = int(len(data) / max_points)
    d = rm3(downsample(data, smooth_factor))

  g.set_data( data )
  g.line( 1, '#333333', label, 1 )

  y_min = min(d)
  if y_min > 0: y_min = 0
  g.set_y_min(y_min)
  g.set_y_max(max(d) + 4)

  g.set_y_label_style( 10, '0x666666')
  g.y_label_steps(4)
  g.set_y_legend('%s %s' % (label,units), 12)

  g.set_x_axis_steps(200)

  #TODO(hobe): add start and end times here
  #TODO(hobe): add note about downsampling and smoothing
  g.set_x_legend('Time', 12)
  g.set_inner_background( '#E3F0FD', '#CBD7E6', 90 )

  return g

def chart_speed(request, activity_id):
  activity = models.Activity.get(activity_id)
  data = activity.speed_list()
  graph = chart_data(data, 'Speed', 'Kph')

  return HttpResponse(graph.render())

def chart_altitude(request, activity_id):
  activity = models.Activity.get(activity_id)
  data = activity.altitude_list()
  graph = chart_data(data, 'Altitude', 'Meters')

  return HttpResponse(graph.render())

def chart_bpm(request, activity_id):
  activity = models.Activity.get(activity_id)
  data = activity.bpm_list()
  graph = chart_data(data, 'Heart Rate', 'BPM')

  return HttpResponse(graph.render())

def chart_cadence(request, activity_id):
  activity = models.Activity.get(activity_id)
  data = activity.cadence_list()
  graph = chart_data(data, 'Cadence', 'RPM')

  return HttpResponse(graph.render())

def dashboard(request, sorting='name'):
  #Add pagination
  user = get_user()
  activity_query = models.Activity.all()
#  activity_query.ancestor(user)
  activity_query.order('-%s' % sorting)
  totals = user.totals()
  return render_to_response('dashboard.html',
    {'activities' : activity_query.fetch(100),
     'totals': totals}
    )


class UploadFileForm(forms.Form):
  file = forms.Field(widget=forms.FileInput())

def upload(request):
  user = get_user()

  if request.method == 'POST':
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
        handle_uploaded_file(user, request.FILES['file'])
        return HttpResponseRedirect('/')
  else:
    form = UploadFileForm()
  return render_to_response('upload.html', {'form': form})


def handle_uploaded_file(user, filedata):
#TODO support gz/bzip/zip files
  activities = pytcx.parse_tcx(filedata)

  for act_dict in activities:
    activity = models.Activity(parent = user, user = user, **act_dict)
    activity.put()
    for lap_dict in act_dict['laps']:
      lap = models.Lap(parent = activity, activity = activity, **lap_dict)
      lap.put()
