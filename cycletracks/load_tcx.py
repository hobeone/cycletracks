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

for file in glob.glob('/home/hobe/garmin/*.tcx'):
  views.handle_uploaded_file(user, file)
