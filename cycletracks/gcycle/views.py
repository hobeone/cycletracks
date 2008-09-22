from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseServerError
from django.template import loader, Context

from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django import forms
from django.conf import settings

from django.contrib.auth import decorators as auth_decorators

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.runtime import DeadlineExceededError

from gcycle import models
from gcycle.lib import pytcx

import zipfile
import tarfile
import bz2
import gzip
import sys
import logging
import md5

def handle_view_exception(request):
  exception = sys.exc_info()
  logging.error("Uncaught exception got through, rendering 500 page")
  logging.error(exception)
  return HttpResponseServerError(
      render_to_string("500.html", {'exception': exception})
  )


@auth_decorators.login_required
def main(request):
  return HttpResponseRedirect('/mytracks/')


def about(request):
  return render_to_response('about.html', {'user' : request.user})


def dashboard_cache_key(user):
  key = '%s-dashboard' % str(user.key())
  return key


@auth_decorators.login_required
def dashboard(request, sorting=None, user=None):
  if user is None:
    user = request.user
  else:
    user = models.User.get(user)

  if sorting is None: sorting = 'start_time'
  key = dashboard_cache_key(user)
  cache_key = dashboard_cache_key(user)
  cached = memcache.get(cache_key)
  if settings.DEBUG: cached = None
  if cached is None or cached['sorting'] != sorting:
    activity_query = models.Activity.all()
    activity_query.ancestor(user)
    activity_query.order('-%s' % sorting)
    activities_exist = activity_query.count(1)
    t = loader.get_template('dashboard.html')
    c = Context({'user_activities' : activity_query,
       'num_activities' :activities_exist,
       'user_totals': user.get_profile().totals,
       'user' : user,
      })
    rendered = t.render(c)
    if not memcache.set(cache_key,
        {'sorting': sorting, 'response': rendered}, 60*120):
      logging.error("Memcache set failed for %s." % cache_key)
    return HttpResponse(rendered)
  else:
    logging.debug('Got cached version of dashboard')
    return HttpResponse(cached['response'])


class UploadFileForm(forms.Form):
  file = forms.Field(widget=forms.FileInput())


@auth_decorators.login_required
def upload(request):
  if request.method == 'POST':
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
      cache_key = dashboard_cache_key(request.user)
      if not memcache.delete(cache_key):
        logging.error("Memcache delete failed.")
      try:
        handle_uploaded_file(request.user, request.FILES['file'])
        return HttpResponseRedirect('/mytracks/')
      except pytcx.TCXExpception, e:
        return render_to_response('error.html', {'error': e})
      except db.NotSavedError, e:
        return render_to_response('error.html', {'error': e})

    else:
      return HttpResponse('Error: Upload errors:\n%s' % repr(form.errors),
          content_type='text/plain')
  else:
    form = UploadFileForm()
  return render_to_response('upload.html', {'form': form, 'user': request.user})


def ziperator(zfile):
  """yields each file in a zipfile
  Args:
    zfile: ZipFile instance

  Returns:
    yields the contents of each file in a zipfile in succession
  """
  files = zfile.namelist()
  for f in files:
    yield zfile.read(f)

def tarerator(tfile):
  """Same as ziperator() but for tarfiles"""
  files = tfile.getnames()
  for f in files:
    yield tfile.extractfile(f).read()

def activity_save(user, activity_dict):
  """Save an activity and laps
  Args:
  - user: User instance, user who will own the activity
  - activity_dict: dict as returned from parse_tcx()

  Returns:
  - Activity object key
  """
  activity = models.Activity(parent = user, user = user, **activity_dict)
  akey = activity.put()
  d = models.SourceDataFile(parent = activity,
      data = activity_dict['tcxdata'],
      activity = activity)
  d.put()
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

  for file in files:
    # fast fail:
    if models.Activity.hash_exists(md5.new(file).hexdigest(), user):
      return HttpResponse('Error: Upload error:\n"An activity with the same source hash already exists"',
        content_type='text/plain')

    activities = pytcx.parse_tcx(file)
    for act_dict in activities:
      db.run_in_transaction(activity_save, user, act_dict)
