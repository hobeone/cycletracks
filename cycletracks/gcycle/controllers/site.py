from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseServerError
from django.template import loader, Context
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django import forms
from django.conf import settings

from django.contrib.auth import decorators as auth_decorators

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.runtime import DeadlineExceededError

from gcycle.models import *
from gcycle.controllers import activity
from gcycle.lib import pytcx

import zipfile
import tarfile
import bz2
import gzip
import sys
import logging
import md5
import re

def handle_view_exception(request):
  exception = sys.exc_info()
  logging.error("Uncaught exception got through, rendering 500 page")
  logging.error(exception)
  return HttpResponseServerError(
      render_to_string("500.html", {'exception': exception})
  )


@auth_decorators.login_required
def main(request):
  return HttpResponseRedirect(reverse('activity_index'))


def about(request):
  return render_to_response('about.html', {'user' : request.user})


class UploadFileForm(forms.Form):
  file = forms.Field(widget=forms.FileInput())
  tags = forms.CharField(max_length=100, required=False)

@auth_decorators.login_required
def upload(request):
  if request.method == 'POST':
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
      try:
        tags = form.cleaned_data['tags']
        if tags:
          tags = tags.split(',')
          tags = map(unicode, tags)
          tags = map(unicode.strip, tags)
        act = handle_uploaded_file(
            request.user, request.FILES['file'], tags=tags)
        return HttpResponseRedirect(act.get_absolute_url())

      except (pytcx.TCXExpception, db.NotSavedError), e:
        return HttpResponse('error: %s' % e, status=501)

    else:
      return HttpResponse('Error: Upload errors:\n%s' % repr(form.errors),
          content_type='text/plain', status=501)
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

def handle_uploaded_file(user, filedata, tags=[]):
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
    act = None
    if re.search(r'xmlns="http://www.topografix.com/GPX/1/0"', file):
      act = Activity.create_from_gpx(file, user, tags)
    else:
      act = Activity.create_from_tcx(file, user, tags)
    act.user.get_profile().update_totals()
    return act
