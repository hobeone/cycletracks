from django.http import *
from django.shortcuts import render_to_response
from django.contrib.auth import decorators as auth_decorators
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users

from gcycle.models import *

from gcycle.lib.pytcx import InvalidTCXFormat
from gcycle.lib.pygpx import InvalidGPXFormat

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
  #acts = Activity.all()
  #for i in acts.fetch(1000):
  #  if i.parsed_at != datetime.datetime(2009, 6, 14, 15, 44, 57, 181874):
  #    i.parsed_at = datetime.datetime(2009, 6, 14, 15, 44, 57, 181874)
  #    i.put()
  #    responses.append('updated act with no parsed_at')

  acts = Activity.all()
  acts.filter('parsed_at <',
      datetime.datetime.utcnow() - datetime.timedelta(hours=2))
  acts.order('-parsed_at')

  count = acts.count()
  responses.append('Found %i remaining activities to reparse' % count)
  for a in acts.fetch(6):
    try:
      a.reparse()
      responses.append('reparsed %s' % a.key().id())
    except db.NotSavedError:
      responses.append('activity %s missing source file' % a.key())
    except InvalidTCXFormat:
      responses.append('not a tcx file')
    except InvalidGPXFormat:
      responses.append('not a gpx file')

  page = """
  <html>
<head>
  <meta http-equiv="refresh" content="5"/>
</head>
<body>
  <h3>Update Datastore</h3>
  %s
</body>
</html>
""" % '<br>'.join(responses)

  return HttpResponse(page)
