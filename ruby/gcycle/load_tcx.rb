#!/usr/bin/env ruby
require File.dirname(__FILE__) + '/config/boot'

require 'lib/rtcx'
require 'pp'
require 'openssl'
require 'English'

tcx_dir = File.dirname(__FILE__) + '/../garmin'
user = User.first

files = []
if ARGV.empty?
  files = Dir.open(tcx_dir).entries
else
  files = ARGV.dup
end
Activity.destroy_all()

files.sort.reverse.each do |file|
  next unless file =~ /.tcx$/
  t = Time.now.to_f
  puts file
  filedata = File.open(tcx_dir + '/' + file).read()
  file_hash = OpenSSL::Digest::MD5.hexdigest(filedata)
  next if Activity.find_by_source_hash(file_hash)
  tcx = TCXParser.new(filedata).parse
  tcx.each do |a|
    a.user = user
    a.name = File.basename(file)
    a.source_hash = file_hash
    a.source_file = SourceFile.new
    a.source_file.filename = File.basename(file)
    a.source_file.filedata = filedata
    a.save!
  end
  puts "#{Time.now.to_f - t}"
end
