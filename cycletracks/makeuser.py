import main
from appengine_django.auth.models import User
from gcycle.models import *
from google.appengine.api import users
import os

os.environ['USER_EMAIL'] = 'test@example.com'
user = users.get_current_user()
print user
u = User(user = user, username = 'test')
u.put()

os.environ['USER_EMAIL'] = 'hobe@example.com'
user = users.get_current_user()
print user
u = User(user = user, username = 'hobe')
u.put()