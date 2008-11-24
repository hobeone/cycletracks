#!/usr/bin/env ruby
require File.dirname(__FILE__) + '/config/boot'

require 'lib/rtcx'
require 'pp'
require 'openssl'
require 'English'
require 'ruby-prof'

tcx_dir = File.dirname(__FILE__) + '/../garmin'
user = User.find_by_login('hobe')

files = []
if ARGV.empty?
  files = Dir.open(tcx_dir).entries
  files = files.map{|f| tcx_dir + '/' + f}
else
  files = ARGV.dup
end
Activity.delete_all()
Lap.delete_all()
SourceFile.delete_all()

files.sort.reverse.each do |file|
  next unless file =~ /.tcx$/
  puts file
  filedata = File.open(tcx_dir + '/' + file).read()
  file_hash = OpenSSL::Digest::MD5.hexdigest(filedata)
  next if Activity.find_by_source_hash(file_hash)
  #RubyProf.start
  t = Time.now.to_f
  Activity.create_from_file!(file, user)
  puts Time.now.to_f - t
  #result = RubyProf.stop
  #measure_names = { RubyProf::MEMORY => 'memory', RubyProf::PROCESS_TIME => 'time' }

  #printer = RubyProf::CallTreePrinter.new(result)
  #printer.print(File.open("callgrind.out.posts_index_#{measure_names[RubyProf::measure_mode]}", 'w'))
  #printer = RubyProf::FlatPrinter.new(result)
  #printer.print(STDOUT, 0)

end
