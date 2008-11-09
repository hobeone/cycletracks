ActionController::Routing::Routes.draw do |map|
  map.home '', :controller => 'dashboard', :action => 'dashboard'

  map.logout   '/logout',   :controller => 'sessions', :action => 'destroy'
  map.login    '/login',    :controller => 'sessions', :action => 'new'
  map.register '/register', :controller => 'users', :action => 'create'
  map.signup   '/signup',   :controller => 'users', :action => 'new'
  map.resources :users

  map.resource :session

  map.root :controller => 'activities'
  map.resources :activities,
    :member => {
      :data => :get,
      :kml => :get,
      :tcx => :get},
    :has_many => :laps

#  map.connect ':controller/:action/:id'
#  map.connect ':controller/:action/:id.:format'
end
