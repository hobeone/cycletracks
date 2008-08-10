from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
  (r'^$', 'gcycle.views.dashboard'),
  (r'^dashboard/(\w+)?/?$', 'gcycle.views.dashboard'),
  (r'^upload/$', 'gcycle.views.upload'),
  (r'^activity/show/(\S+)$', 'gcycle.activity.show'),
  (r'^activity/graph/(\S+)$', 'gcycle.activity.graph'),
  (r'^activity/update/$', 'gcycle.views.activity_update'),
)
