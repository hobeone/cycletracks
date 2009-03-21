#!/bin/sh
find -name \*.pyc -print0 | xargs -0 rm
perl -p -i -e 's/DEBUG = True/DEBUG = False/' settings.py
python2.5 manage.py update
perl -p -i -e 's/DEBUG = False/DEBUG = True/' settings.py
