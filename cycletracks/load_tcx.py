#!/usr/bin/python
import main
from gcycle.models import *

from gcycle.lib import pytcx
import glob
import pprint
pp = pprint.PrettyPrinter(indent=2)
from appengine_django.auth.models import User
from google.appengine.api import users
import os
import sys
import time

user = User.all().fetch(1)[0]

files = glob.glob('/home/hobe/garmin/*.tcx')
if sys.argv[1:2]:
  files = sys.argv[1:2]
files.sort()
for file in files:
  print file
  stime = time.time()
  try:
    Activity.create_from_tcx(open(file).read(), user)
  except pytcx.TCXExpception, e:
    print e
  print '%.4f seconds' % (time.time() - stime)
