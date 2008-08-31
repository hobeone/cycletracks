from django.http import *
from django.shortcuts import render_to_response
from django.contrib.auth import decorators as auth_decorators
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users

from gcycle.models import *

@auth_decorators.login_required
def users(request):
  user = request.user
  allusers = User.all()

  return render_to_response('admin/users.html', {'user': user, 'users': allusers})
