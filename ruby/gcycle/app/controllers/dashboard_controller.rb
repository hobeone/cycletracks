class DashboardController < ApplicationController
  before_filter :login_required
  layout "base"
  def dashboard
    @page_title = 'Dashboard'
    @activities = Activity.find_all_by_user_id(current_user.id)
    @user_totals = current_user.totals
  end
end
