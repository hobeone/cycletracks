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

@auth_decorators.login_required
def update_users(request):
  response = []
  users = UserProfile.all()
  for u in users:
    u.update_totals()
    response.append('updated %s' % u)

  return HttpResponse('<br/>'.join(response))

@auth_decorators.login_required
def update_acts(request):
  response = []
  for s in SourceDataFile.all():
    s.delete()

  for l in Lap.all():
    l.delete()

  for a in Activity.all():
    a.delete()


  return HttpResponse('<br/>'.join(response))

@auth_decorators.login_required
def reparse_activity(request):
  responses = []
  acts = Activity.all()

  acts.filter('parsed_at <',
      datetime.datetime.utcnow() - datetime.timedelta(day=1))

  for a in acts.fetch(4):
    try:
      a.reparse()
      responses.append('reparsed %s' % a.key())
    except db.NotSavedError:
      responses.append('activity %s missing source file' % a.key())

  return HttpResponse('<br>'.join(responses))