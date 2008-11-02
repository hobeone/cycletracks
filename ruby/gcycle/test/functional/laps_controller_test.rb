require 'test_helper'

class LapsControllerTest < ActionController::TestCase
  def test_should_get_index
    get :index
    assert_response :success
    assert_not_nil assigns(:laps)
  end

  def test_should_get_new
    get :new
    assert_response :success
  end

  def test_should_create_lap
    assert_difference('Lap.count') do
      post :create, :lap => { }
    end

    assert_redirected_to lap_path(assigns(:lap))
  end

  def test_should_show_lap
    get :show, :id => laps(:one).id
    assert_response :success
  end

  def test_should_get_edit
    get :edit, :id => laps(:one).id
    assert_response :success
  end

  def test_should_update_lap
    put :update, :id => laps(:one).id, :lap => { }
    assert_redirected_to lap_path(assigns(:lap))
  end

  def test_should_destroy_lap
    assert_difference('Lap.count', -1) do
      delete :destroy, :id => laps(:one).id
    end

    assert_redirected_to laps_path
  end
end
