from django.conf.urls.defaults import *

from gcycle import controllers

handler500 = 'gcycle.controllers.site.handle_view_exception'
urlpatterns = patterns('',
  (r'^$', 'gcycle.controllers.site.main'),
  (r'^mytracks/(?P<sorting>\S+)?$', 'gcycle.controllers.activity.index'),
  (r'^upload/$', 'gcycle.controllers.site.upload'),
  (r'^about/$', 'gcycle.controllers.site.about'),
  (r'^admin/users/$', 'gcycle.controllers.admin.users'),
  (r'^admin/update_users/$', 'gcycle.controllers.admin.update_users'),
  (r'^admin/update_acts/$', 'gcycle.controllers.admin.update_acts'),
  (r'^admin/reparse_activity/$', 'gcycle.controllers.admin.reparse_activity'),
  (r'^admin/dashboard/(?P<user>\S+)$', 'gcycle.controllers.activity.index'),
  (r'^activity/show/(\S+)$', 'gcycle.controllers.activity.show'),
  (r'^activity/data/(\S+)$', 'gcycle.controllers.activity.data'),
  (r'^activity/source/(\S+)$', 'gcycle.controllers.activity.source'),
  (r'^activity/public/(\S+)$', 'gcycle.controllers.activity.public'),
  (r'^activity/delete/$', 'gcycle.controllers.activity.delete'),
  (r'^activity/kml/(\S+)$', 'gcycle.controllers.activity.activity_kml'),
  (r'^activity/update/$', 'gcycle.controllers.activity.update'),
  (r'^activity/tag/(.+)$', 'gcycle.controllers.activity.tag'),
  (r'^user/settings/$', 'gcycle.controllers.user.settings'),
  (r'^user/update/$', 'gcycle.controllers.user.update'),
)
