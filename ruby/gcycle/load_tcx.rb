#!/usr/bin/env ruby
require File.dirname(__FILE__) + '/config/boot'

require 'lib/rtcx'
require 'pp'
require 'openssl'

tcx_dir = File.dirname(__FILE__) + '/../garmin'

Dir.open(tcx_dir) do |dir|
  dir.each do |file|
    next unless file =~ /.tcx$/
      t = Time.now.to_f
      puts file
      filedata = File.open(tcx_dir + '/' + file).read()
      tcx = TCXParser.new(filedata).parse
      puts "#{Time.now.to_f - t}"
      tcx.each do |a|
        a.name = file
        a.source_hash = OpenSSL::Digest::MD5.hexdigest(filedata)
        a.save!
      end
  end
end
