from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
import django.utils.safestring
from gcycle.models import Activity, Lap
from gcycle import views
from gcycle.lib import glineenc
from django.contrib.auth import decorators as auth_decorators
from django.contrib.auth.models import User

from google.appengine.api import datastore_errors
from google.appengine.api import memcache
import logging

@auth_decorators.login_required
def settings(request):
  return render_to_response('user/settings.html',
      {'user': request.user, 'offsets': ','.join(map(str,range(-14,12)))})

VALID_USER_ATTRIBUTES = ['use_imperial', 'tzoffset']

@auth_decorators.login_required
def update(request):
  try:
    update_user = User.get(request.POST['user_id'])
    user_attribute = request.POST['attribute']
    user_value = request.POST['update_value']

    if update_user != request.user:
      return render_to_response('error.html',
        {'error': "You are not allowed to edit this user"})


    # LAME
    if user_attribute == 'use_imperial':
      if user_value == 'False':
        user_value = False
      else:
        user_value = True
    if user_attribute == 'tzoffset':
      user_value = int(user_value)

    if user_attribute in VALID_USER_ATTRIBUTES:
      if getattr(update_user.get_profile(), user_attribute) != user_value:
        setattr(update_user.get_profile(), user_attribute, user_value)
        update_user.get_profile().save()
      if not memcache.delete(views.dashboard_cache_key(request.user)):
        logging.error("Memcache delete failed.")
      return HttpResponse(user_value)
  except Exception, e:
    return HttpResponse(e)
