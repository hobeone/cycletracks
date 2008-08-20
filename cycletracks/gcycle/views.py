from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseServerError
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django import forms

from django.contrib.auth import decorators as auth_decorators

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users

from gcycle import models
from gcycle.lib import pytcx



import zipfile
import tarfile
import bz2
import gzip
import sys
import logging

def handle_view_exception(request):
  exception = sys.exc_info()
  logging.error("Uncaught exception got through, rendering 500 page")
  logging.error(exception)
  return HttpResponseServerError(
      render_to_string("500.html", {'exception': exception})
  )


@auth_decorators.login_required
def main(request):
  user = request.user
  return HttpResponseRedirect('/mytracks/')


@auth_decorators.login_required
def clean_broken_acts(request):
  q = models.Activity.all()
  for a in q:
    if db.get(a._user) is None:
      a.delete()
  return HttpResponseRedirect('/mytracks/')


@auth_decorators.login_required
def about(request):
  return render_to_response('about.html', {'user' : request.user})


@auth_decorators.login_required
def dashboard(request, sorting='start_time'):
  if sorting == None: sorting = 'start_time'
  activity_query = models.Activity.all()
  activity_query.ancestor(request.user)
  activity_query.order('-%s' % sorting)
  activities_exist = activity_query.count(1)
  stats = memcache.get_stats()
  return render_to_response('dashboard.html',
    {'user_activities' : activity_query,
     'num_activities' :activities_exist,
     'user_totals': request.user.get_profile().totals,
     'user' : request.user,
     'stats' : stats,}
    )

class UploadFileForm(forms.Form):
  file = forms.Field(widget=forms.FileInput())

@auth_decorators.login_required
def upload(request):
  if request.method == 'POST':
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
      try:
        handle_uploaded_file(request.user, request.FILES['file'])
        return HttpResponseRedirect('/mytracks/')
      except pytcx.TCXExpception, e:
        return render_to_response('error.html', {'error': e})
  else:
    form = UploadFileForm()
  return render_to_response('upload.html', {'form': form, 'user': request.user})


def ziperator(zfile):
  files = zfile.namelist()
  for f in files:
    yield zfile.read(f)

def tarerator(tfile):
  files = tfile.getnames()
  for f in files:
    yield tfile.extractfile(f).read()

def activity_save(user, activity_dict):
  activity = models.Activity(parent = user, user = user, **activity_dict)
  akey = activity.put()
  for lap_dict in activity_dict['laps']:
    lap = models.Lap(parent = activity, activity = activity, **lap_dict)
    lap.put()

  return akey

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
      db.run_in_transaction(activity_save, user, act_dict)
