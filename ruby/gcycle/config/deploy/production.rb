#############################################################
#Application
#############################################################

set :application, "gcycle"
set :deploy_to, "/var/gcycle"

#############################################################
#Settings
#############################################################

default_run_options[:pty] = true
ssh_options[:forward_agent] = true
set :use_sudo, true
set :scm_verbose, true
set :rails_env, "staging"

#############################################################
#Servers
#############################################################

set :user, "hobe"
set :domain, "packetspike.net"
server domain, :app, :web
role :db, domain, :primary => true

#############################################################
#Source
#############################################################

set :scm, :subversion
set :repository, "https://cycletracks.googlecode.com/svn/ruby/gcycle"
set :deploy_via, :export

#############################################################
#Passenger
#############################################################

require 'openssl'

namespace :deploy do
  desc 'Check that session_secret exists locally'
  task :before_update_code do
    if  !File.readable?('session_secret.encrypted')
      raise "session_secret file doesn't exist or is not readable"
    end
    c = OpenSSL::Cipher::Cipher.new("aes-256-cbc")
    c.decrypt
    c.key = OpenSSL::Digest::SHA512.hexdigest(
      Capistrano::CLI.password_prompt(
        "Session Key Password: "
      )
    )
    d = c.update(File.read('session_secret.encrypted'))
    d << c.final
    $decrypted_session_key = d.to_s
  end

  desc "Create the database yaml file"
  task :after_update_code do
    db_config = <<-EOF
    staging:
      adapter: mysql
      encoding: utf8
      username: root
      password:
      database: gcycle_staging
      host: localhost
    EOF

    put db_config, "#{release_path}/config/database.yml"

    put($decrypted_session_key,
      "#{release_path}/session_secret", :mode => 0444)

  end

  # Restart passenger on deploy
  desc "Restarting mod_rails with restart.txt"
  task :restart, :roles => :app, :except => { :no_release => true } do
    run "touch #{current_path}/tmp/restart.txt"
  end

  [:start, :stop].each do |t|
    desc "#{t} task is a no-op with mod_rails"
    task t, :roles => :app do ; end
  end

end
