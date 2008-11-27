#!/usr/bin/ruby
require 'openssl'
require 'rubygems'
require 'capistrano'
require 'capistrano/cli'

c = OpenSSL::Cipher::Cipher.new("aes-256-cbc")
c.encrypt
# your pass is what is used to encrypt/decrypt
c.key = OpenSSL::Digest::SHA512.hexdigest(
  Capistrano::CLI.password_prompt
)
e = c.update(File.read('session_secret'))
e << c.final
File.open('session_secret.encrypted', 'w+').write(e)
