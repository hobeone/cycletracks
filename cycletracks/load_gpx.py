#!/usr/bin/python2.5
from common.appenginepatch.aecmd import setup_env
setup_env(manage_py_env=True)
from gcycle.models import *

from gcycle.lib import pygpx
import glob
import pprint
pp = pprint.PrettyPrinter(indent=2)
from ragendja.auth.google_models import User

from google.appengine.api import users
import os
import sys
import time

user = User.all().fetch(1)[0]

files = glob.glob('/home/hobe/garmin/*.gpx')
if sys.argv[1:2]:
  files = sys.argv[1:2]
files.sort()
for file in files:
  print file
  stime = time.time()
  act = Activity.create_from_gpx(open(file).read(), user, version = '1/0')
  act.user.get_profile().update_totals()
  print '%.4f seconds' % (time.time() - stime)
