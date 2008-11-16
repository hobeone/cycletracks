require 'test_helper'
require 'pp'
class ActiveSupport::Cache::MemoryStore
  attr_reader :data
end


class ActivitiesControllerTest < ActionController::TestCase
  def setup
    Rails.cache.clear
  end

  def test_should_get_index
    login_as(:hobe)
    get :index
    assert_response :success
    assert_not_nil assigns(:activities)
  end

  def test_should_cache_index
    login_as(:hobe)
    get :index
    hobe_cache_path = 'views/' + @controller.action_cache_path.path
    hobe_results_cache = Rails.cache.read(hobe_cache_path)
    assert_not_nil hobe_results_cache
    assert_response :success
    assert_not_nil assigns(:activities)
  end

  def test_should_cache_show
    login_as(:hobe)
    get :show, :id => activities(:activity_one).id
    hobe_cache_path = 'views/' + @controller.action_cache_path.path
    pp hobe_cache_path
    hobe_results_cache = Rails.cache.read(hobe_cache_path)
    assert_not_nil hobe_results_cache
    assert_response :success
    assert_not_nil assigns(:activity)
  end

  def test_should_cache_data
    login_as(:hobe)
    get :data, :id => activities(:activity_one).id
    hobe_cache_path = 'views/' + @controller.action_cache_path.path
    hobe_results_cache = Rails.cache.read(hobe_cache_path)
    assert_not_nil hobe_results_cache
    assert_response :success
    assert_not_nil assigns(:activity)
  end

  def test_should_get_new
    login_as(:hobe)
    get :new
    assert_response :success
  end

  def test_should_create_activity
    login_as(:hobe)
    assert_difference('Activity.count') do
      post :create, :tcx_file =>
        fixture_file_upload('valid_multi_lap.tcx', 'text/xml')
    end

    assert_redirected_to activity_path(assigns(:activity))
  end

  def test_should_show_activity
    login_as(:hobe)
    get :show, :id => activities(:activity_one).id
    assert_response :success
  end

  def test_should_update_activity
    login_as(:hobe)
    put :update, :id => activities(:activity_one).id, :activity => { }
    assert_redirected_to activity_path(assigns(:activity))
  end

  def test_should_destroy_activity
    login_as(:hobe)
    assert_difference('Activity.count', -1) do
      delete :destroy, :id => activities(:activity_one).id
    end

    assert_redirected_to activities_path
  end
end
