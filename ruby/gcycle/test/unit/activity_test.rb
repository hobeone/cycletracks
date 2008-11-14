require 'test_helper'

class ActivityTest < ActiveSupport::TestCase
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
    assert_valid(a)
  end
end
