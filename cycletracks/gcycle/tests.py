import unittest
import datetime
import os

from gcycle.models import *
from gcycle.controllers import site
from gcycle.controllers import activity
from gcycle.lib import pytcx
from gcycle.lib import pygpx

from google.appengine.api import datastore_errors
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import apiproxy_stub_map

from ragendja.auth.google_models import User

from django.test.client import Client

import pprint
pp = pprint.PrettyPrinter(indent=2)

# Other test files
from gcycle.test.test_activity_controller import *
from gcycle.test.test_site_controller import *
from gcycle.test.test_activity_model import *
from gcycle.test.test_lap_model import *
from gcycle.test.test_custom_db_types import *

class testModel(db.Model):
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
    self.assertEqual(act['total_time'], 26162)

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

class testGpxParser(unittest.TestCase):
  def Gpx10Contents(self, data):
    """Return a GPX 1.0 file containing data."""
    return ("""<?xml version="1.0"?><gpx version="1.0"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns="http://www.topografix.com/GPX/1/0"
xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">"""
            + data + """</gpx>""")

  def Gpx11Contents(self, data):
    """Return a GPX 1.1 file containing data."""
    return ("""<?xml version="1.0"?><gpx version="1.1" creator="" 
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns="http://www.topografix.com/GPX/1/1"
xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">"""
            + data + """</gpx>""")

  def testValidParse10(self):
    testfile = open('gcycle/test/valid_single_segment_10.gpx').read()
    act = pygpx.parse_gpx(testfile, '1/0')
    self.assertFalse('maximum_bpm' in act)
    self.assertFalse('total_calories' in act)
    self.assertEqual(act['end_point'], '37.996776,-122.506612')
    self.assertFalse('average_bpm' in act)
    self.assertFalse('average_cadence' in act)
    self.assertAlmostEqual(act['average_speed'], 10.224, 2)
    self.assertFalse('maximum_bpm' in act)
    self.assertFalse('maximum_cadence' in act)
    self.assertAlmostEqual(act['maximum_speed'], 18.29, 2)
    self.assertEqual(len(act['laps']), 1)
    self.assertFalse('total_calories' in act)
    self.assertAlmostEqual(act['total_meters'], 139.16, 2)
    self.assertEqual(act['total_time'], 49)

    u = User(username = 'test', user = users.User('test@ex.com'))
    u.put()
    a = Activity(user = u, **act)
    self.assert_(a)
    a.put()
    for l in act['laps']:
      lap = Lap(activity = a, **l)
      lap.put()

      self.assertEqual(len(lap.speed_list), len(lap.altitude_list))
      self.assertFalse(lap.cadence_list)
      self.assertFalse(lap.bpm_list)
      self.assertEqual(len(lap.speed_list), len(lap.timepoints))
      self.assertEqual(len(lap.speed_list), len(lap.geo_points))

      self.assertAlmostEqual(lap.total_ascent, 12.8, 2)
      self.assertAlmostEqual(lap.total_descent, 3.22, 2)

    self.assertAlmostEqual(a.total_ascent, 12.8, 2)
    self.assertAlmostEqual(a.total_descent, 3.22, 2)

  def testEmptyLap(self):
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx10Contents(""), '1/0')
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx11Contents(""), '1/1')

  def testOnePointSegment(self):
    one_point_trk = """<trk>
  <name>ACTIVE LOG105449</name>
  <trkseg>
  <trkpt lat="37.996256" lon="-122.507784">
    <ele>272.165</ele>
    <time>2009-03-21T18:42:45Z</time>
  </trkpt>
  </trkseg></trk>"""
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx10Contents(one_point_trk), '1/0')
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx11Contents(one_point_trk), '1/1')

  def testTwoPointSegment(self):
    two_point_trk = """<trk><trkseg>
  <trkpt lat="37.996364" lon="-122.50774199999999">
    <ele>273.50599999999997</ele>
    <time>2009-03-21T18:42:51Z</time>
  </trkpt>
  <trkpt lat="37.996462999999999" lon="-122.507684">
    <ele>273.89600000000002</ele>
    <time>2009-03-21T18:42:57Z</time>
  </trkpt>
  </trkseg></trk>"""
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx10Contents(two_point_trk), '1/0')
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx11Contents(two_point_trk), '1/1')

  def testThreePointSegment(self):
    three_point_trk = """<trk><trkseg>
  <trkpt lat="37.996364" lon="-122.50774199999999">
    <ele>273.50599999999997</ele>
    <time>2009-03-21T18:42:51Z</time>
  </trkpt>
  <trkpt lat="37.996462999999999" lon="-122.507684">
    <ele>273.89600000000002</ele>
    <time>2009-03-21T18:42:57Z</time>
  </trkpt>
  <trkpt lat="37.996588000000003" lon="-122.507561">
    <ele>271.34199999999998</ele>
    <time>2009-03-21T18:43:03Z</time>
  </trkpt>
  </trkseg></trk>"""
    activity_record = pygpx.parse_gpx(self.Gpx10Contents(three_point_trk),
                                      '1/0')
    self.assertEqual(len(activity_record['laps']), 1)
    self.assertAlmostEqual(activity_record['total_meters'], 29.9, 2)

    activity_record = pygpx.parse_gpx(self.Gpx11Contents(three_point_trk),
                                      '1/1')
    self.assertEqual(len(activity_record['laps']), 1)
    self.assertAlmostEqual(activity_record['total_meters'], 29.9, 2)


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
    self.assertEqual(UserProfile.all().filter('user =', u).count(), 0)
    profile = u.get_profile()
    self.assertEquals(profile.user, u)
    self.assertEquals(profile.activity_count, 0)

  def tearDown(self):
    for u in User.all():
      u.delete()
