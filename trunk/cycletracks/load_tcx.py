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
import sys
import time

user = User.all().fetch(1)[0]
pp.pprint(user)

files = glob.glob('/home/hobe/garmin/*.tcx')
if sys.argv[1:2]:
  files = sys.argv[1:2]
files.sort()
for file in files:
  stime = time.time()
  try:
    views.handle_uploaded_file(user, open(file))
  except pytcx.TCXExpception, e:
    print e
  print '%.4f seconds' % (time.time() - stime)
