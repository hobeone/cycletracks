require 'test_helper'

class ActivityTest < ActiveSupport::TestCase
  def test_name_is_required
    a = Activity.new()
    a.name = nil
    assert(!a.valid?)
    a.name = 'foo'
    a.start_time = Time.now
    a.end_time = a.start_time - 10
    a.laps = ['1']
    a.user = 'foo'
    assert_valid(a)
  end
end
