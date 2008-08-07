#!/bin/sh
rm -rf django/bin
rm -rf django/contrib/admin
rm -rf django/contrib/admindocs
rm -rf django/contrib/syndication
rm -rf django/contrib/gis
rm -rf django/contrib/databrowse
rm -rf django/contrib/localflavor
find -name \*.pyc -print0 | xargs -0 rm
./.google_appengine/appcfg.py update .
