from django.http import HttpResponseRedirect

from google.appengine.api import users

def login_required(function):
  """Implementation of Django's login_required decorator.

  The login redirect URL is always set to request.path
  """
  def login_required_wrapper(request, *args, **kw):
    if request.user.is_authenticated():
      return function(request, *args, **kw)
    return HttpResponseRedirect(users.create_login_url(request.path))
  return login_required_wrapper
