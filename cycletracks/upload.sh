#!/bin/sh
find -name \*.pyc -print0 | xargs -0 rm
./.google_appengine/appcfg.py update .
