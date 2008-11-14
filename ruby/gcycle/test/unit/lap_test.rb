require 'test_helper'

class LapTest < ActiveSupport::TestCase
  def test_validation
    l = laps(:one)
    assert_valid(l)
  end
end
