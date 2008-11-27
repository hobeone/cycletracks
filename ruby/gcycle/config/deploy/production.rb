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
set :rails_env, "production"

#############################################################
#Servers
#############################################################

set :user, "hobe"
set :domain, "lorien.corp.google.com"
server domain, :app, :web
role :db, domain, :primary => true

#############################################################
#Source
#############################################################

set :scm, :subversion
set :repository, "https://cycletracks.googlecode.com/svn/ruby/gcycle"
#set :branch, "master"
#set :scm_user, 'bort'
#set :scm_passphrase, "PASSWORD"
set :deploy_via, :remote_cache

#############################################################
#Passenger
#############################################################

require 'openssl'
require 'digest/sha1'


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
    production:
      adapter: mysql
      encoding: utf8
      username: root
      password:
      database: gcycle_production
      host: localhost
    EOF

    put db_config, "#{release_path}/config/database.yml"

    #########################################################
    # Uncomment the following to symlink an uploads directory.
    # Just change the paths to whatever you need.
    #########################################################

    # desc "Symlink the upload directories"
    # task :before_symlink do
    #   run "mkdir -p #{shared_path}/uploads"
    #   run "ln -s #{shared_path}/uploads #{release_path}/public/uploads"
    # end

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
