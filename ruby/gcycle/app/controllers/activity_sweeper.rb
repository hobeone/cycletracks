class ActivitySweeper < ActionController::Caching::Sweeper
  observe Activity
  def after_destroy(activity)
    expire_cache_for(activity)
  end

  private
  def expire_cache_for(activity)
    expire_fragment(%r'views/.*/activities/#{activity.user.login}.+_activities_index_page_')
  end
end
