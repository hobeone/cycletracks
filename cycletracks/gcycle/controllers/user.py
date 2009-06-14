from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
import django.utils.safestring

from gcycle.models import Activity, Lap
from gcycle.controllers import activity
from gcycle.lib import glineenc
from django.contrib.auth import decorators as auth_decorators
from django.contrib.auth.models import User

from google.appengine.api import datastore_errors
from google.appengine.api import memcache
import logging

from django import forms
from timezones import forms as tzforms

class UserForm(forms.Form):
  user_id = forms.CharField(required=True, widget=forms.HiddenInput)
  timezone =  tzforms.TimeZoneField(required=True)
  use_imperial = forms.BooleanField(required=False)
  default_public = forms.BooleanField(required=False)

@auth_decorators.login_required
def settings(request):

  if request.method == 'POST': # If the form has been submitted...
    form = UserForm(request.POST) # A form bound to the POST data


    if form.is_valid(): # All validation rules pass
      update_user = User.get(form.cleaned_data['user_id'])
      if update_user != request.user:
        return render_to_response('error.html',
        {'error': "You are not allowed to edit this user"})

      update_user.get_profile().timezone = str(form.cleaned_data['timezone'])
      update_user.get_profile().use_imperial = form.cleaned_data['use_imperial']
      update_user.get_profile().default_public = \
          form.cleaned_data['default_public']
      update_user.put()
      update_user.get_profile().put()
      return HttpResponseRedirect('/a/') # Redirect after POST
  else:
    data = {'username' : request.user.username,
            'timezone' : request.user.get_profile().timezone,
            'use_imperial' : request.user.get_profile().use_imperial,
            'default_public' : request.user.get_profile().default_public,
            'user_id': str(request.user.key()),
           }
    form = UserForm(data) # An unbound form

  return render_to_response('user/settings.html',
      {
       'form': form,
       'data': data,
      }
  )
