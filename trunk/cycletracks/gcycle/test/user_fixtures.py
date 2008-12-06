from fixture import DataSet
import datetime
import google.appengine.api.users as users

class UserData(DataSet):
  class admin_user:
    username = 'admin'
    first_name = None
    last_name = None
    is_active = True
    is_superuser = True
    is_staff = True
    last_login = datetime.datetime.utcnow()
    user = users.User(email='admin@foo.com', _auth_domain='google.com')
    password = None
    email = None
    date_joined = datetime.datetime.utcnow()

  class normal_user:
    username = 'joe'
    first_name = 'Joe'
    last_name = 'Blow'
    is_active = True
    is_superuser = False
    is_staff = False
    last_login = datetime.datetime.utcnow()
    user = users.User(email='joeblow@foo.com', _auth_domain='google.com')
    password = None
    email = None
    date_joined = datetime.datetime.utcnow()
