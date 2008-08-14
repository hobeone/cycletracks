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
from google.appengine.api import memcache
from django.views.decorators.cache import cache_page

from django.conf.urls.defaults import *
from django.views.generic import list_detail

import zipfile
import tarfile
import bz2
import gzip

class UserNotExist(Exception):
  pass

def getUserAccount():
  gaia_user = users.get_current_user()
  q = db.GqlQuery("SELECT * FROM User WHERE user = :1", gaia_user)
  user = q.get()
  return user

def get_user():
  user = getUserAccount()
  if not user: raise UserNotExist(
      "User %s doesn't exist" % users.get_current_user())
  return user

def main(request):
  user = getUserAccount()
  if not user:
    return render_to_response('signup.html',
        {'gaia_user' : users.get_current_user()})
  else:
    return HttpResponseRedirect('/mytracks/')

def newuser(request):
  user = users.get_current_user()
  u = models.User(user = user, username = str(user))
  u.put()
  return HttpResponseRedirect('/mytracks/')

def about(request):
  user = get_user()
  return render_to_response('about.html', {'user' : user})

def dashboard(request, sorting='start_time'):
  if sorting == None: sorting = 'start_time'
  user = get_user()
  activity_query = models.Activity.all()
  activity_query.ancestor(user)
  activity_query.order('-%s' % sorting)
  activities_exist = activity_query.count(1)
  stats = memcache.get_stats()
  return render_to_response('dashboard.html',
    {'user_activities' : activity_query,
     'num_activities' :activities_exist,
     'user_totals': user.totals(),
     'user' : user,
     'stats' : stats,}
    )

def getCurUserTotals():
  return get_user().totals()

class UploadFileForm(forms.Form):
  file = forms.Field(widget=forms.FileInput())

def upload(request):
  user = get_user()

  if request.method == 'POST':
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
      try:
        handle_uploaded_file(user, request.FILES['file'])
        return HttpResponseRedirect('/mytracks/')
      except pytcx.UnknownTCXExpception, e:
        return render_to_response('error.html', {'error': e})
  else:
    form = UploadFileForm()
  return render_to_response('upload.html', {'form': form, 'user': user})


def ziperator(zfile):
  files = zfile.namelist()
  for f in files:
    yield zfile.read(f)

def tarerator(tfile):
  files = tfile.getnames()
  for f in files:
    yield tfile.extractfile(f).read()

def handle_uploaded_file(user, filedata):
  files = []
  # .zip
  try:
    files = ziperator(zipfile.ZipFile(filedata, 'r'))
  except zipfile.BadZipfile, e:
    pass

  # .bz2
  if not files:
    try:
      filedata.seek(0)
      files = [bz2.decompress(filedata.read())]
    except IOError, e:
      pass

  # .gz
  if not files:
    try:
      filedata.seek(0)
      files = [gzip.GzipFile(fileobj=filedata).read()]
    except IOError, e:
      pass

  # .tar.bz2 or .tar.gz
  if not files:
    try:
      filedata.seek(0)
      files = tarerator(tarfile.open(fileobj=filedata, mode='r'))
    except tarfile.ReadError, e:
      pass

  # plain text
  if not files:
    filedata.seek(0)
    files = [filedata.read()]

  for f in files:
    activities = pytcx.parse_tcx(f)
    for act_dict in activities:
      activity = models.Activity(parent = user, user = user, **act_dict)
      activity.put()
      for lap_dict in act_dict['laps']:
        lap = models.Lap(parent = activity, activity = activity, **lap_dict)
        lap.put()
