require 'test_helper'
require 'lib/rtcx'


class ActivityTest < ActiveSupport::TestCase
  def test_parse_good
    file = 'test/fixtures/valid_exported.tcx'
    activity = Activity.create_from_file!(file, User.first)[0]
    puts activity.time_list.length
    puts activity.bpm_list.length
    puts activity.altitude_list.length
    puts activity.distance_list.length
    puts activity.speed_list.length
    puts activity.cadence_list.length
  end

  def test_name_is_required
    a = Activity.new()
    a.name = nil
    assert(!a.valid?)
    a.name = 'foo'
    assert(!a.valid?)
    a.start_time = Time.now
    assert(!a.valid?)
    a.end_time = a.start_time - 10
    assert(!a.valid?)
    a.laps = [Lap.first]
    assert(!a.valid?)
    a.user = User.first
    assert(!a.valid?)
    a.source_file = SourceFile.first
    a.compute_data_from_laps!
    assert_valid(a)
  end
end
