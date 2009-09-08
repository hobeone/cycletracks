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

from django.contrib.auth.models import User

from django.test.client import Client

import pprint
pp = pprint.PrettyPrinter(indent=2)

# Other test files
from gcycle.test.test_activity_controller import *
from gcycle.test.test_site_controller import *
from gcycle.test.test_activity_model import *
from gcycle.test.test_stats_model import *
from gcycle.test.test_lap_model import *
from gcycle.test.test_custom_db_types import *


class testTcxParser(unittest.TestCase):
  multiline_tag = """<b>
asd
asd
  </b>"""

  multiline_val_tag = """<b>
<Value>123</Value>
</b>"""

  power_tag = """<Extensions>
  <TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
    <Watts>404</Watts>
  </TPX>
</Extensions>"""

  def testParseZulu(self):
    valid_format = '2008-06-01T13:55:04Z'
    invalid_format = 'fooT13:55:04Z'
    self.assert_(pytcx.parse_zulu(valid_format))
    self.assertRaises(ValueError, pytcx.parse_zulu, invalid_format)

  def testParseOfShortTcx(self):
    testfile = open('gcycle/test/invalid_tcx.tcx').read()
    self.assertRaises(
        pytcx.InvalidTCXFormat,
        pytcx.parse_tcx,
        testfile
        )

  def testParseOfTcxWithErrors(self):
    testfile = open('gcycle/test/valid_multi_lap_with_short_lap.tcx').read()
    acts = pytcx.parse_tcx(testfile)
    act = acts[0]
    u = User(username = 'test', user = users.User('test@ex.com'))
    u.put()
    a = Activity._put_activity_record(act, u, 'tcx',
                                      'source, which is ignored')

    self.assert_(a)
    self.assertEqual(len(a.sourcedatafile_set.get().parse_errors), 1)

  def testValidPowerParse(self):
    testfile = open('gcycle/test/valid_activity_with_power.tcx').read()
    acts = pytcx.parse_tcx(testfile)
    self.assertEqual(len(acts), 1)
    activity = acts[0]
    self.assertEqual(activity['average_power'], 173)
    self.assertEqual(activity['maximum_power'], 794)
    u = User(username = 'test', user = users.User('test@ex.com'))
    u.put()

    a = Activity._put_activity_record(activity, u, 'tcx',
                                      'source, which is ignored')

    self.assertEqual(a.lap_set.count(), 2)
    laps = a.lap_set.fetch(2)
    self.assertEqual(laps[0].maximum_power, 585)
    self.assertEqual(laps[1].maximum_power, 794)
    self.assertEqual(laps[0].average_power, 322)
    self.assertEqual(laps[1].average_power, 162)

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

    a = Activity._put_activity_record(act, u, 'tcx',
                                      'source, which is ignored')

    self.assert_(a)
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

  def putActivity(self, activity_record):
    """Make sure app engine doesn't barf when putting activity_record."""
    user = User(username = 'test', user = users.User('test@ex.com'))
    user.put()
    return Activity._put_activity_record(activity_record, user, 'gpx',
                                         'source, which is ignored')

  def  assertAlmostEqualIter(self, iterable_a, iterable_b, places):
    """Assert that two iterables have same length and almost equal elements."""
    self.assertEqual(len(iterable_a), len(iterable_b))
    for a, b in zip(iterable_a, iterable_b):
      self.assertAlmostEqual(a, b, places)

  def testValidParse10(self):
    testfile = open('gcycle/test/valid_single_segment_10.gpx').read()
    act = pygpx.parse_gpx(testfile, '1/0')
    self.assertFalse('maximum_bpm' in act)
    self.assertFalse('total_calories' in act)
    self.assertEqual(act['end_point'], '37.996776,-122.506612')
    self.assertFalse('average_bpm' in act)
    self.assertFalse('average_cadence' in act)
    self.assertEqual(act['rolling_time'], 49)
    self.assertAlmostEqual(act['average_speed'], 10.14, 1)
    self.assertFalse('maximum_bpm' in act)
    self.assertFalse('maximum_cadence' in act)
    self.assertAlmostEqual(act['maximum_speed'], 18.26, 1)
    self.assertEqual(len(act['laps']), 1)
    self.assertFalse('total_calories' in act)
    self.assertAlmostEqual(act['total_meters'], 138.13, 1)
    self.assertEqual(act['total_time'], 49)

    a = self.putActivity(act)
    for lap in a.lap_set:
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

  def testParseGpxZeroDivisionError(self):
    three_point_trk = """
 <trk>
  <name>ACTIVE LOG002128</name>
  <trkseg>
   <trkpt lat="37.772741" lon="-122.451556">
    <ele>2369.704</ele>
    <time>2009-03-21T07:21:28Z</time>
   </trkpt>
   <trkpt lat="37.772695" lon="-122.451573">
    <ele>2372.282</ele>
    <time>2009-03-21T07:35:15Z</time>
   </trkpt>
   <trkpt lat="37.772697" lon="-122.451577">
    <ele>2372.042</ele>
    <time>2009-03-21T07:37:17Z</time>
   </trkpt>
  </trkseg>
 </trk>
"""
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx10Contents(three_point_trk), '1/0')

  def testFourPointSegment(self):
    four_point_trk = """<trk><trkseg>
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
  <trkpt lat="37.996668999999997" lon="-122.507492">
    <ele>270.67200000000003</ele>
    <time>2009-03-21T18:43:05Z</time>
  </trkpt>
  </trkseg></trk>"""
    activity_record = pygpx.parse_gpx(self.Gpx10Contents(four_point_trk),
                                      '1/0')
    self.assertEqual(len(activity_record['laps']), 1)
    self.assertAlmostEqual(activity_record['total_meters'], 40.53, 1)
    self.putActivity(activity_record)

    activity_record = pygpx.parse_gpx(self.Gpx11Contents(four_point_trk),
                                      '1/1')
    self.assertEqual(len(activity_record['laps']), 1)
    self.assertAlmostEqual(activity_record['total_meters'], 40.53, 1)
    self.putActivity(activity_record)

  def testNoRollingTime(self):
    no_time_delta_trk = """<trk><trkseg>
  <trkpt lat="37.996668999999997" lon="-122.507492">
    <ele>270.67200000000003</ele>
    <time>2009-03-21T18:43:05Z</time>
  </trkpt>
  <trkpt lat="37.996710999999998" lon="-122.507448">
    <ele>270.74799999999999</ele>
    <time>2009-03-21T18:43:05Z</time>
  </trkpt>
  <trkpt lat="37.996822000000002" lon="-122.507234">
    <ele>272.46899999999999</ele>
    <time>2009-03-21T18:43:05Z</time>
  </trkpt>
  <trkpt lat="37.996836000000002" lon="-122.507113">
    <ele>274.017</ele>
    <time>2009-03-21T18:43:05Z</time>
  </trkpt>
  </trkseg></trk>"""
    self.assertRaises(pygpx.InvalidGPXFormat, pygpx.parse_gpx,
                      self.Gpx10Contents(no_time_delta_trk), '1/0')

  def testNoMovementSegment(self):
    bad_good_segments = """<trk><name>No movement</name><trkseg>
  <trkpt lat="37.996364" lon="-122.507741">
    <ele>273.505999</ele>
    <time>2009-03-21T18:42:51Z</time>
  </trkpt>
  <trkpt lat="37.996364" lon="-122.507741">
    <ele>273.896000</ele>
    <time>2009-03-21T18:42:57Z</time>
  </trkpt>
  <trkpt lat="37.996364" lon="-122.507741">
    <ele>271.341999</ele>
    <time>2009-03-21T18:43:03Z</time>
  </trkpt>
  </trkseg></trk>
<trk><name>Good track to make sure parsing finishes</name><trkseg>
  <trkpt lat="37.996668999999997" lon="-122.507492">
    <ele>270.67200000000003</ele>
    <time>2009-03-21T18:43:05Z</time>
  </trkpt>
  <trkpt lat="37.996710999999998" lon="-122.507448">
    <ele>270.74799999999999</ele>
    <time>2009-03-21T18:43:06Z</time>
  </trkpt>
  <trkpt lat="37.996822000000002" lon="-122.507234">
    <ele>272.46899999999999</ele>
    <time>2009-03-21T18:43:12Z</time>
  </trkpt>
  <trkpt lat="37.996836000000002" lon="-122.507113">
    <ele>274.017</ele>
    <time>2009-03-21T18:43:17Z</time>
  </trkpt>
</trkseg>
</trk>
"""
    activity_record = pygpx.parse_gpx(self.Gpx11Contents(bad_good_segments),
                                      '1/1')
    a = self.putActivity(activity_record)
    self.assertEqual(len(a.lap_set), 1)
    self.assertAlmostEqual(activity_record['total_meters'], 39.27, 2)

  def testAverageSpeedGreaterThanMax(self):
    # An older algorithm for finding speed from a list of points caused the
    # average speed to be greater than the max speed for this data. This
    # happened because the speed list was found using a moving average over 3 
    # calculated speeds and sometimes the speed was incorrectly calculated to
    # be 0.
    odd_trk = """
 <trk>
  <name>ACTIVE LOG211421</name>
  <trkseg>
   <trkpt lat="38.378753" lon="-108.934550">
    <ele>1631.432</ele>
    <time>2009-08-27T03:14:21Z</time>
   </trkpt>
   <trkpt lat="38.379000" lon="-108.934602">
    <ele>1631.244</ele>
    <time>2009-08-27T03:14:28Z</time>
   </trkpt>
   <trkpt lat="38.379461" lon="-108.934525">
    <ele>1632.419</ele>
    <time>2009-08-27T03:14:49Z</time>
   </trkpt>
  </trkseg>
 </trk>"""
    activity_record = pygpx.parse_gpx(self.Gpx11Contents(odd_trk),
                                      '1/1')
    a = self.putActivity(activity_record)
    self.assertEqual(len(a.lap_set), 1)
    #self.assertEqual(a.lap_set[0].speed_list, 1)
    self.assertAlmostEqual(activity_record['total_meters'], 79.405, 2)

  def testDuplicateTimes(self):
    """Make sure the speed calculation removes the first duplicated time."""
    odd_trk = """
 <trk>
  <name>ACTIVE LOG211421</name>
  <trkseg>
   <trkpt lat="38.378753" lon="-108.934550">
    <ele>1631.432</ele>
    <time>2009-08-27T03:14:21Z</time>
   </trkpt>
   <trkpt lat="38.378753" lon="-108.934550">
    <ele>1631.432</ele>
    <time>2009-08-27T03:14:21Z</time>
   </trkpt>
   <trkpt lat="38.379000" lon="-108.934602">
    <ele>1631.244</ele>
    <time>2009-08-27T03:14:28Z</time>
   </trkpt>
   <trkpt lat="38.379461" lon="-108.934525">
    <ele>1632.419</ele>
    <time>2009-08-27T03:14:49Z</time>
   </trkpt>
  </trkseg>
 </trk>"""
    activity_record = pygpx.parse_gpx(self.Gpx11Contents(odd_trk),
                                      '1/1')
    a = self.putActivity(activity_record)
    self.assertEqual(len(a.lap_set), 1)
    self.assertEqual(len(a.lap_set[0].speed_list), 3)
    self.assertAlmostEqualIter(
        a.lap_set[0].speed_list, [14.29, 14.29, 8.85], 2)
    self.assertAlmostEqual(activity_record['total_meters'], 79.405, 2)


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
