import unittest
import datetime
import os

from gcycle.models import *
from gcycle.controllers import site
from gcycle.controllers import activity
from gcycle.lib import pytcx

from google.appengine.api import datastore_errors
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import apiproxy_stub_map

from appengine_django.auth.models import User
from appengine_django.models import BaseModel

from django.test.client import Client

import pprint
pp = pprint.PrettyPrinter(indent=2)

# Other test files
from gcycle.test.test_activity_controller import *

class testModel(BaseModel):
  csv = CsvListProperty(str)

class testCsvListPropery(unittest.TestCase):

  def testModel(self):
    list = range(1,1000)
    list = map(str,list)
    c = testModel( csv = list)
    key = c.put()
    c = testModel.get(key)
    self.failUnlessEqual(c.csv, list)

    c.csv.append('testing')
    c.put()
    c = testModel.get(key)
    self.failUnlessEqual(c.csv[-1], 'testing')


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

  def testValidParse(self):
    testfile = open('gcycle/test/valid_multi_lap.tcx').read()
    acts = pytcx.parse_tcx(testfile)
    self.assertEqual(len(acts), 1)
    act = acts[0]
    self.assertEqual(act['maximum_bpm'], 186)
    self.assertEqual(act['total_calories'], 6754.0)
    self.assertEqual(act['end_point'], '37.773787,-122.439899')
    self.assertEqual(act['average_bpm'], 136)
    self.assertEqual(act['average_cadence'], 80)
    self.assertAlmostEqual(act['average_speed'], 14.326339080604534, 2)
    self.assertEqual(act['maximum_bpm'], 186)
    self.assertEqual(act['maximum_cadence'], 81)
    self.assertAlmostEqual(act['maximum_speed'], 56.35, 2)
    self.assertEqual(len(act['laps']), 2)
    self.assertEqual(act['total_calories'], 6754.0)
    self.assertAlmostEqual(act['total_meters'], 78993.84, 2)
    self.assertEqual(act['total_time'], 26164)

    u = User(username = 'test', user = users.User('test@ex.com'))
    u.put()
    a = Activity(user = u, **act)
    self.assert_(a)
    a.put()
    for l in act['laps']:
      lap = Lap(activity = a, **l)
      lap.put()

      self.assertEqual(len(lap.speed_list), len(lap.altitude_list))
      self.assertEqual(len(lap.speed_list), len(lap.cadence_list))
      self.assertEqual(len(lap.speed_list), len(lap.bpm_list))
      self.assertEqual(len(lap.speed_list), len(lap.timepoints))
      self.assertEqual(len(lap.speed_list), len(lap.geo_points))

      self.assertEqual(lap.total_ascent, 0)
      self.assertAlmostEqual(lap.total_descent, 9.1319, 2)

    self.assertEqual(a.total_ascent, 0)
    self.assertAlmostEqual(a.total_descent, 18.263, 2)

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
    self.assertEquals(profile.activity_count, 0)

  def tearDown(self):
    for u in User.all():
      u.delete()

class ActivityTestCase(unittest.TestCase):
  def setUp(self):
    apiproxy_stub_map.apiproxy.GetStub('datastore_v3').Clear()
    self.gaia_user = users.User('f@e.com')
    self.app_user = User(user = self.gaia_user, username = 'bar')
    self.app_user.put()

  def testCreateFromTcx(self):
    testfile = open('gcycle/test/valid_multi_lap.tcx').read()
    a = Activity.create_from_tcx(testfile, self.app_user)

  def testActivityTags(self):
    a = Activity(
        user = self.app_user,
        name = 'foo',
        sport = 'bar',
        total_meters = 4.0,
        start_time = datetime.datetime.utcnow(),
        end_time = datetime.datetime.utcnow(),
        total_time = 2,
        rolling_time = 2,
        average_speed = 2.0,
        maximum_speed = 2.0,
        source_hash = 'foobaz',
    )
    a.tags = "foo, bar"
    a.put()
    for a in db.GqlQuery("SELECT * from Activity WHERE tags = 'foo'"):
      print a.name
      print a.tags


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
        source_hash = 'foobaz',
    )
    a.put()
    self.app_user.delete()
    a = Activity.get(a.key())
    self.assert_(a)
    self.assertRaises(db.Error, getattr, a, 'user')
    self.assertEqual(None, a.safeuser)
