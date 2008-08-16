import unittest
import datetime
import os

from gcycle.models import *
from gcycle import views
from gcycle.lib import pytcx

from google.appengine.api import datastore_errors
from google.appengine.ext import db
from google.appengine.api import users

from appengine_django.auth.models import User

from django.test.client import Client

class testTcxParser(unittest.TestCase):
  multiline_tag = """<b>
asd
asd
  </b>"""

  multiline_val_tag = """<b>
<Value>123</Value>
</b>"""

  def testParseZulu(self):
    valid_format = '2008-06-01T13:55:04Z'
    invalid_format = 'fooT13:55:04Z'
    self.assert_(pytcx.parse_zulu(valid_format))
    self.assertRaises(ValueError, pytcx.parse_zulu, invalid_format)

  def testGetTagVal(self):
    self.assert_(pytcx.getTagVal('<b>foo</b>', 'b', None))
    self.assertEqual("asd\nasd", pytcx.getTagVal(self.multiline_tag, 'b', None))
    # Default to None
    self.assertEqual(None, pytcx.getTagVal('','b'))

  def testGetIntTagVal(self):
    self.assertEqual('123', pytcx.getIntTagVal('<int>123</int>','int', None))

  def testGetTagSubVal(self):
    val = pytcx.getIntTagSubVal(self.multiline_val_tag, 'b', None)
    self.assertEqual(123, val)

  def testParseOfShortTcx(self):
    testfile = open('gcycle/test/invalid_tcx.tcx').read()
    self.assertRaises(
        pytcx.InvalidTCXFormat,
        pytcx.parse_tcx,
        testfile
        )

class testMainViews(unittest.TestCase):
  def setUp(self):
    os.environ['USER_EMAIL'] = 'test@unitttest.com'
    self.c = Client()

  def testFrontPageAutoSignup(self):
    self.assertEqual(User.all().count(), 0)
    response = self.c.get('/')
    self.assertEqual(302,response.status_code)
    self.assertEqual(User.all().count(), 1)

  def testFrontPageRealUser(self):
    self.app_user = User(user = users.get_current_user(), username = 'bar')
    self.app_user.put()
    response = self.c.get('/')
    self.assertEqual(302,response.status_code)
    self.assert_('http://testserver/mytracks/' in str(response))

  def tearDown(self):
    for u in User.all():
      u.delete()


class UserTestCase(unittest.TestCase):
  def test_required_fields(self):
    self.assertRaises(datastore_errors.BadValueError, User, user = 'foo')
    self.assertRaises(datastore_errors.BadValueError, User, user = 'foo@ex.com',
        username = 'bar')

  def testWorksWithRealUser(self):
    ex_user = users.User('f@e.com')
    u = User(user = ex_user, username = 'bar')
    u.put()
    self.assert_(u.key())

  def testAutoProfileCreate(self):
    ex_user = users.User('f@e.com')
    u = User(user = ex_user, username = 'bar')
    u.put()
    self.assert_(u.key())
    self.assertEqual(UserProfile.all().count(), 0)
    profile = u.get_profile()
    self.assertEquals(profile.user, u)
    self.assert_(profile.totals)
    self.assertEquals(profile.activity_count, 0)

  def tearDown(self):
    for u in User.all():
      u.delete()


class ActivityTestCase(unittest.TestCase):
  def setUp(self):
    self.gaia_user = users.User('f@e.com')
    self.app_user = User(user = self.gaia_user, username = 'bar')
    self.app_user.put()


  def test_safe_user(self):
    a = Activity(
        user = self.app_user,
        name = 'foo',
        sport = 'bar',
        total_meters = 0.0,
        start_time = datetime.datetime.utcnow(),
        end_time = datetime.datetime.utcnow(),
        total_time = 0,
        rolling_time = 0,
        average_speed = 0.0,
        maximum_speed = 0.0,
    )
    a.put()
    self.app_user.delete()
    a = Activity.get(a.key())
    self.assert_(a)
    self.assertRaises(db.Error, getattr, a, 'user')
    self.assertEqual(None, a.safeuser)
