from gcycle.models import Activity, Lap, User
from google.appengine.api import users
import os

os.environ['USER_EMAIL'] = 'test@example.com'
user = users.get_current_user()
print user
u = User(user = user, username = 'test')
u.put()
