#!/usr/bin/python
import main
from gcycle.models import *

from gcycle.lib import pytcx
import glob
import pprint
pp = pprint.PrettyPrinter(indent=2)
from gcycle import views
from appengine_django.auth.models import User
from google.appengine.api import users
import os
import time

user = User.all().fetch(1)[0]
files = glob.glob('/home/hobe/garmin/*.tcx')
files.sort()
for file in files:
  stime = time.time()
  print file
  try:
    views.handle_uploaded_file(user, open(file))
  except pytcx.TCXExpception, e:
    print e
  print '%.4f seconds' % (time.time() - stime)
