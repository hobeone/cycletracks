from django.template.loader import get_template
from django.template import Context, RequestContext
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django import forms

from google.appengine.api import users

from gcycle import models
from gcycle.lib import pytcx

from google.appengine.ext import db

def get_user():
  gaia_user = users.get_current_user()
  return models.User.get_or_insert(
      gaia_user.email(),
      user = gaia_user,
      username = str(gaia_user))


def dashboard(request, sorting='start_time'):
  if sorting == None: sorting = 'start_time'
  #Add pagination
  user = get_user()
  activity_query = models.Activity.all()
  activity_query.ancestor(user)
  activity_query.order('-%s' % sorting)
  totals = user.totals()
  return render_to_response('dashboard.html',
    {'user_activities' : activity_query.fetch(100),
     'user_totals': totals,
     'user' : user}
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
  return render_to_response('upload.html', {'form': form, 'user': user})

def handle_uploaded_file(user, filedata):
#TODO support gz/bzip/zip files
  activities = pytcx.parse_tcx(filedata)
  for act_dict in activities:
    activity = models.Activity(parent = user, user = user, **act_dict)
    activity.put()
    for lap_dict in act_dict['laps']:
      lap = models.Lap(parent = activity, activity = activity, **lap_dict)
      lap.put()
