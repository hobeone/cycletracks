from gcycle.lib import pytcx
import glob
import pprint
pp = pprint.PrettyPrinter(indent=4)
from gcycle.models import Activity, Lap
from gcycle import views
from google.appengine.api import users
import os

os.environ['USER_EMAIL'] = 'test@example.com'
user = views.get_user()
files = glob.glob('/home/hobe/garmin/*.tcx')
files.sort()
for file in files:
  print file
  views.handle_uploaded_file(user, open(file))
