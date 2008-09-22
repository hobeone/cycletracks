#!/usr/bin/python
import os
import httplib
import urllib
import urllib2
import cookielib
import mimetools, mimetypes
import os
import stat
import sys
from cStringIO import StringIO
import getpass
from optparse import OptionParser
import glob

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

# Controls how sequences are uncoded. If true, elements may be given multiple values by
#  assigning a sequence.
doseq = 1

class MultipartPostHandler(urllib2.BaseHandler):
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is not None and type(data) != str:
            v_files = []
            v_vars = []
            try:
                 for(key, value) in data.items():
                     if type(value) == file:
                         v_files.append((key, value))
                     else:
                         v_vars.append((key, value))
            except TypeError:
                systype, value, traceback = sys.exc_info()
                raise TypeError, "not a valid non-string sequence or mapping object", traceback

            if len(v_files) == 0:
                data = urllib.urlencode(v_vars, doseq)
            else:
                boundary, data = self.multipart_encode(v_vars, v_files)

                contenttype = 'multipart/form-data; boundary=%s' % boundary
                if(request.has_header('Content-Type')
                   and request.get_header('Content-Type').find('multipart/form-data') != 0):
                    print "Replacing %s with %s" % (request.get_header('content-type'), 'multipart/form-data')
                request.add_unredirected_header('Content-Type', contenttype)

            request.add_data(data)

        return request

    def multipart_encode(vars, files, boundary = None, buf = None):
        if boundary is None:
            boundary = mimetools.choose_boundary()
        if buf is None:
            buf = StringIO()
        for(key, value) in vars:
            buf.write('--%s\r\n' % boundary)
            buf.write('Content-Disposition: form-data; name="%s"' % key)
            buf.write('\r\n\r\n' + value + '\r\n')
        for(key, fd) in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = fd.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            buf.write('--%s\r\n' % boundary)
            buf.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
            buf.write('Content-Type: %s\r\n' % contenttype)
            # buffer += 'Content-Length: %s\r\n' % file_size
            fd.seek(0)
            buf.write('\r\n' + fd.read() + '\r\n')
        buf.write('--' + boundary + '--\r\n\r\n')
        buf = buf.getvalue()
        return boundary, buf
    multipart_encode = Callable(multipart_encode)

    https_request = http_request


class CtUploader(object):
  def __init__(self, username, password):
    self.username = username
    self.password = password
    self.app_hostname = 'cycletracks.appspot.com'
    self.redir_target = 'upload/'
    self.app_name = "cycletracks-1.0"

    # we use a cookie to authenticate with Google App Engine
    #  by registering a cookie handler here, this will automatically store the
    #  cookie returned when we use urllib2 to open http://currentcost.appspot.com/_ah/login
    self.cookiejar = cookielib.LWPCookieJar()

  def google_login(self):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
    urllib2.install_opener(opener)

    #
    # get an AuthToken from Google accounts
    #
    auth_uri = 'https://www.google.com/accounts/ClientLogin'
    authreq_data = urllib.urlencode({ "Email":   self.username,
                                      "Passwd":  self.password,
                                      "service": "ah",
                                      "source":  self.app_name,
                                      "accountType": "HOSTED_OR_GOOGLE" })
    auth_req = urllib2.Request(auth_uri, data=authreq_data)
    try:
      auth_resp = urllib2.urlopen(auth_req)
    except urllib2.HTTPError, e:
      print "Error logging into Google, perhaps you mistyped your password"
      sys.exit(1)

    auth_resp_body = auth_resp.read()
    # auth response includes several fields - we're interested in
    #  the bit after Auth=
    auth_resp_dict = dict(x.split("=")
                          for x in auth_resp_body.split("\n") if x)
    authtoken = auth_resp_dict["Auth"]

    #
    # get a cookie
    #
    #  the call to request a cookie will also automatically redirect us to the page
    #   that we want to go to
    #  the cookie jar will automatically provide the cookie when we reach the
    #   redirected location

    # this is where I actually want to go to
    serv_uri = 'http://%s/%s' % (self.app_hostname, self.redir_target)

    serv_args = {}
    serv_args['continue'] = serv_uri
    serv_args['auth']     = authtoken

    full_serv_uri = 'http://%s/_ah/login?%s' % (self.app_hostname,
        urllib.urlencode(serv_args))

    serv_req = urllib2.Request(full_serv_uri)
    serv_resp = urllib2.urlopen(serv_req)
    serv_resp_body = serv_resp.read()


  def upload_file(self,filename):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar),
                                  MultipartPostHandler)
    upload_uri = 'http://cycletracks.appspot.com/upload/'
    params = { "file" : open(filename, "rb") }
    opener.open(upload_uri, params).read()


  def upload_dir(self, directory):
    for filename in sorted(glob.glob(os.path.join(directory, '*.tcx'))):
      print "Uploading %s" % filename
      self.upload_file(filename)


if __name__=="__main__":

  parser = OptionParser()
  parser.add_option("-u", "--user", dest="username",
                  help="USER to login as", metavar="USER")
  parser.add_option("-d", "--directory", dest="directory",
                  help="DIRECTORY containing files to upload", metavar="DIRECTORY")

  (options, args) = parser.parse_args()
  if options.username is None or options.directory is None:
    print "Missing required argument"
    parser.print_help()
    sys.exit(1)

  password = getpass.getpass('Enter your password: ')

  directory = '/home/hobe/garmin'
  u = CtUploader(options.username, password)
  u.google_login()
  print "Got a google cookie to use..."
  u.upload_dir(options.directory)
