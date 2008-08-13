from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
import django.utils.safestring
from gcycle.models import Activity, Lap, User
from gcycle import views
from gcycle.lib import glineenc

from google.appengine.api import datastore_errors
from google.appengine.api import memcache
import logging

def settings(request):
  user = views.get_user()
  return render_to_response('user/settings.html', {'user': user})

VALID_USER_ATTRIBUTES = ['use_imperial']

def update(request):
  try:
    user = views.get_user()
    update_user = User.get(request.POST['user_id'])
    user_attribute = request.POST['attribute']
    user_value = request.POST['value']

    if update_user != user:
      return render_to_response('error.html',
        {'error': "You are not allowed to edit this user"})


    # LAME
    if user_attribute == 'use_imperial':
      if user_value == 'False':
        user_value = False
      else:
        user_value = True

    if user_attribute in VALID_USER_ATTRIBUTES:
      if getattr(update_user, user_attribute) != user_value:
        setattr(update_user, user_attribute, user_value)
        update_user.put()
      return HttpResponse(user_value)
  except Exception, e:
    return HttpResponse(e)
