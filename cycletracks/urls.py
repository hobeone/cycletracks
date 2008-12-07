from django.conf.urls.defaults import *

from gcycle import controllers

handler500 = 'gcycle.controllers.site.handle_view_exception'
urlpatterns = patterns('gcycle.controllers',
  (r'^$', 'site.main'),
  url(r'^upload/$', 'site.upload', name='upload'),
  (r'^about/$', 'site.about'),
  (r'^admin/users/$', 'admin.users'),
  (r'^admin/update_users/$', 'admin.update_users'),
  (r'^admin/update_acts/$', 'admin.update_acts'),
  (r'^admin/reparse_activity/$', 'admin.reparse_activity'),
  (r'^admin/dashboard/(?P<user>\S+)$', 'activity.index'),
  url(r'^a/$',                  'activity.index',  name='activity_index'),
  url(r'^a/(?P<sorting>\D+)$', 'activity.index', name='activity_sorted_index'),
  # dispatches to show or update depending on HTTP method
  url(r'^a/(\d+)$',         'activity.show',   name='activity_show'),
  # GFE don't support DELETE method apparently, otherwise we could use the
  # above path on that method.
  url(r'^a/(\d+)\.delete$', 'activity.delete',   name='activity_delete'),
  url(r'^a/(\d+)\.pub$',    'activity.public', name='activity_public'),
  url(r'^a/(\d+)\.data$',   'activity.data',   name='activity_data'),
  url(r'^a/(\d+)\.kml$',    'activity.kml',    name='activity_kml'),
  url(r'^a/(\d+)\.source$', 'activity.source', name='activity_source'),
  url(r'^a/(\d+)\.data$',   'activity.data',   name='activity_data'),
  url(r'^t/(.+)$', 'activity.tag', name='tags_index'),
  (r'^user/settings/$', 'user.settings'),
  (r'^user/update/$', 'user.update'),
)
