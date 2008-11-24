require 'digest/sha1'

class User < ActiveRecord::Base
  include Authentication
  include Authentication::ByPassword
  include Authentication::ByCookieToken

  has_many :activities, :dependent => :destroy


  validates_presence_of     :login
  validates_length_of       :login,    :within => 3..40
  validates_uniqueness_of   :login
  validates_format_of       :login,    :with => Authentication.login_regex, :message => Authentication.bad_login_message

  validates_format_of       :name,     :with => Authentication.name_regex,  :message => Authentication.bad_name_message, :allow_nil => true
  validates_length_of       :name,     :maximum => 100

  validates_presence_of     :email
  validates_length_of       :email,    :within => 6..100 #r@a.wk
  validates_uniqueness_of   :email
  validates_format_of       :email,    :with => Authentication.email_regex, :message => Authentication.bad_email_message

  def validate
    if !ActiveSupport::TimeZone::MAPPING.include?(read_attribute(:timezone))
      errors.add(:timezone, "is not in the valid list")
    end
  end

  def timezone
    return @tz_cache unless @tz_cache.nil?
    tz_string = read_attribute(:timezone)
    @tz_cache = ActiveSupport::TimeZone.new(tz_string)
    if @tz_cache.nil?
      @tz_cache = ActiveSupport::TimeZone.new("UTC")
    end
    return @tz_cache
  end

  def timezone=(tz)
    if tz.instance_of?(ActiveSupport::TimeZone)
      write_attribute(:timezone, tz.name)
    else
      write_attribute(:timezone, tz)
    end
  end

  def to_user_localtime(time_with_zone)
    time_with_zone.in_time_zone(self.timezone)
  end

  def totals
    return @total_cache unless @total_cache.nil?
    @total_cache = {
      :total_meters => activities.sum(:total_meters) || 0.0,
      :total_time => activities.sum(:total_time) || 0.0 ,
      :total_ascent => activities.sum(:total_ascent) || 0.0,
      :rolling_time => activities.sum(:rolling_time) || 0,
      :average_cadence => activities.average(:average_cadence) || 0,
      :maximum_cadence => activities.maximum(:maximum_cadence) || 0,
      :average_bpm => activities.average(:average_bpm) || 0,
      :maximum_bpm => activities.maximum(:maximum_bpm) || 0,
      :average_speed => activities.average(:average_speed) || 0.0,
      :maximum_speed => activities.maximum(:maximum_speed) || 0.0,
      :total_calories => activities.sum(:total_calories) || 0,
    }
    return @total_cache
  end

  # HACK HACK HACK -- how to do attr_accessible from here?
  # prevents a user from submitting a crafted form that bypasses activation
  # anything else you want your user to change should be added here.
  attr_accessible :login, :email, :name, :password, :password_confirmation, :metric, :timezone


  # Authenticates a user by their login name and unencrypted password.  Returns the user or nil.
  #
  # uff.  this is really an authorization, not authentication routine.  
  # We really need a Dispatch Chain here or something.
  # This will also let us return a human error message.
  #
  def self.authenticate(login, password)
    return nil if login.blank? || password.blank?
    u = find_by_login(login) # need to get the salt
    u && u.authenticated?(password) ? u : nil
  end

  def login=(value)
    write_attribute :login, (value ? value.downcase : nil)
  end

  def email=(value)
    write_attribute :email, (value ? value.downcase : nil)
  end

  protected
end
