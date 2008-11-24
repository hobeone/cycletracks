ActionController::Routing::Routes.draw do |map|
  map.home '', :controller => 'activities', :action => 'index'

  map.logout   '/logout',   :controller => 'sessions', :action => 'destroy'
  map.login    '/login',    :controller => 'sessions', :action => 'new'
  map.register '/register', :controller => 'users', :action => 'create'
  map.signup   '/signup',   :controller => 'users', :action => 'new'
  map.resources :users,
    :has_many => :activities,
    :only => [:index, :show, :update]

  map.resource :session

  map.root :controller => 'activities'
  map.resources :activities,
    :member => {
      :data => :get,
    },
    :collection => {
      :tags => :get,
      :search => :get,
    }

#  map.connect ':controller/:action/:id'
#  map.connect ':controller/:action/:id.:format'
end
