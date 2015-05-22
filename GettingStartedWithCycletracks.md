# Introduction #
I develop on Ubuntu Linux, so these instructions are for skewed for that distro.
  * install subversion and python + python-dev
    * sudo apt-get install subversion python python-dev python-setuptools

  * install support libs:
    * http://pypi.python.org/pypi/fixture/
    * easy\_install fixture


  * svn co http://cycletracks.googlecode.com/svn/trunk/cycletracks cycletracks
  * cd cycletracks
  * ./manage.py runserver
  * point your browser to http://localhost:8000
  * ./manage test gcycle to run tests


Code layout:
  * Controller code is in:
    * gcycle/controllers/

  * Views are in:
    * gcycle/templates/

  * Models are all in:
    * gcycle/models.py

  * Tests are in:
    * gcycle/tests.py
    * gcycle/tests/

  * Misc code and tcx/gpx parsers are in
    * gcycle/lib/

Helper scripts:
  * bulk\_uploader.py is a script that will upload the given files to cycletracks in bulk
  * diffchanges.sh is a wrapper around tkdiff to walk through changed files in the subversion client
  * load\_tcx.py and load\_gpx.py are scripts that load a directory of tcx or gpx files into the development data store.

Notes:
  * I'm using svn versions of django and appengine\_django plugins so there are a few warning of deprecated features when you start the server.
  * I hate XML, Python and Django