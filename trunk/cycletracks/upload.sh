#!/bin/sh
find -name \*.pyc -print0 | xargs -0 rm
perl -p -i -e 's/DEBUG = True/DEBUG = False/' settings.py
./.google_appengine/appcfg.py update .
perl -p -i -e 's/DEBUG = False/DEBUG = True/' settings.py
