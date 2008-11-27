require 'lib/rtcx'

class ActivitiesController < ApplicationController
  include ApplicationHelper

  before_filter :login_required, :except => [:show, :data]
  before_filter :authorize_index_view, :only => [ :index ]
  before_filter :authorize_views, :only => [:show, :data]
  before_filter :authorize_mods, :only => [:update, :destroy]
  layout "base"
  cache_sweeper :activity_sweeper, :only => [ :destroy ]

  def authorize_index_view
    return true if @current_user.admin?
    return true if params[:user_id] == @current_user.id.to_s
    return true if params[:user_id].nil?
    render :text => 'Access to that resource denied', :status => 401
  end

  def authorize_mods
    @activity = Activity.find(params[:id])
    return true if @activity.user = @current_user
    return true if @current_user.admin?
    if (request.xhr?)
      format.json { render :json => @activity, :status => 500}
    end

    render :text => 'Access to that resource denied', :status => 401
  end

  def authorize_views
    @activity = Activity.find(params[:id])
    return true if @activity.public?
    if logged_in?
      return true if @activity.user = @current_user
      return true if @current_user.admin?
      if (request.xhr?)
        format.json { render :json => @activity, :status => 500}
      end
    else
      render :text => 'Access to that resource denied', :status => 401
    end
  end

  caches_action :index, :cache_path => Proc.new { |controller|
    controller.send(:activities_url) + '/' +
    controller.send(:current_user).login +
    controller.send(:current_user).metric.to_s +
    '_activities_index_page_' + controller.params[:page].to_s
  }
  caches_action :index, :cache_path => Proc.new { |controller|
    index_cache_key(controller)
  }

  def self.index_cache_key(controller)
    return controller.send(:activities_url) + '/' +
           controller.send(:current_user).login +
           controller.send(:current_user).metric.to_s +
           controller.send(:current_user).activities.maximum(:updated_at).to_i.to_s+
           '_activities_index_page_' + controller.params[:page].to_s
  end

  def index
    params[:page] ||= 1
    Activity.send(:with_scope, :find => {
      :conditions => ['user_id = ?', @current_user.id]}) do
      if Activity.count > 0
        if stale?(:last_modified => Activity.maximum(:updated_at).utc,
                  :etag => [@current_user]
                 )
          @activities = Activity.paginate(
            :all,
            :page => params[:page],
            :order => 'start_time DESC',
            :include => :tags,
            :per_page => 15
          )
          @page_title = 'dashboard'
          respond_to do |format|
            format.html # index.html.erb
            format.xml  { render :xml => @activities }
          end
        end
      else
        @activities = Activity.paginate :all, :page => params[:page],
          :order => 'start_time DESC'
      end
    end
  end

  def tags
    params[:page] ||= 1

    Activity.send(:with_scope,
                  :find => {
      :conditions => ['user_id = ? or public = ?', @current_user.id, true]}) do
      tags = params[:tags]
      opts = Activity.find_options_for_find_tagged_with(tags).merge(
        :page => params[:page],
        :per_page => 15,
        :order => 'start_time DESC'
      )
      @activities = Activity.paginate(opts)
    end
    render :action => "index"
  end

  def search
    if params[:q]
      params[:page] ||= 1
      params[:include_public] ||= false

      opts = Activity.find_options_for_find_tagged_with(params[:q]).merge(
        :page => params[:page],
        :per_page => 15,
        :order => 'start_time DESC'
      )
      restrict = 'user_id = :user_id'
      if params[:include_public]
        restrict = restrict + ' OR public = :include_public'
      end
      opts[:conditions] = [
        "(#{opts[:conditions]} OR comment LIKE :q) AND (#{restrict})",
        params.merge(
          :user_id => @current_user.id
        )
      ]
      begin
        @activities = Activity.paginate(opts)
      rescue ActiveRecord::StatementInvalid => e
        logger.error(e)
        @error = 'Invalid Search query'
        render :template => 'shared/500', :layout => nil, :status => '500'
      end
    else
      render :template => 'activities/search_form'
    end
  end

  caches_action :show, :data, :cache_path => Proc.new { |controller|
    view_cache_key(controller)
  }

  def self.view_cache_key(controller)
    user_key = ''
    if controller.send(:logged_in?)
      user_key = controller.send(:current_user).login +
                 controller.send(:current_user).metric.to_s
    end
    return controller.send(:activity_url) + '/' +
           user_key + '_activity_' + controller.action_name +
           controller.params[:id].to_s
  end

  def show
    response.last_modified = @activity.updated_at.utc
    response.etag = [@activity, @current_user]
    if stale?(:last_modified => @activity.updated_at.utc,
              :etag => [@activity, @current_user])
      respond_to do |format|
        format.kml do
          render :template => 'activities/kml', :layout => false
        end
        format.tcx do
          headers['Content-Disposition'] = 'attachment; filename=' +
            @activity.source_file.filename
          render :text => @activity.source_file.filedata, :layout => false
        end
        @page_title = @activity.name
        format.html # show.html.erb
        format.xml  { render :xml => @activity }
      end
    end
  end

  def data
    data = @activity.time_list.zip(
      @activity.altitude_list,
      @activity.speed_list,
      @activity.cadence_list,
      @activity.distance_list,
      @activity.bpm_list
    )
    activity_data = []
    st = @activity.user.to_user_localtime(@activity.start_time.in_time_zone)

    data.each do |time,alt,speed,cad,dist,bpm|
      activity_data << [
        (st + time).strftime('%FT%T'),
        meters_to_prefered_small_distance(alt),
        mps_to_prefered_speed(speed),
        cad,
        meters_to_prefered_distance(dist),
        bpm
      ].join(',')
    end
    headers["Content-Type"] = "text/plain; charset=utf-8"
    render :text => activity_data.join("\n")
  end

  def new
    @activity = Activity.new

    respond_to do |format|
      format.html # new.html.erb
      format.xml  { render :xml => @activity }
    end
  end

  def create
    tcx_data = params[:tcx_file].read()
    file_hash = OpenSSL::Digest::MD5.hexdigest(tcx_data)
    tcx = TCXParser.new(tcx_data).parse
    @activity = tcx[0]
    @activity.user = current_user
    @activity.name = params[:tcx_file].original_filename
    @activity.source_hash = file_hash
    @activity.source_file = SourceFile.new
    @activity.source_file.filename = params[:tcx_file].original_filename
    @activity.source_file.filedata = tcx_data

    respond_to do |format|
      if @activity.save
        @activity.tag_list = params[:tags_list]
        @activity.save
        expire_action(self.class.index_cache_key(self))
        #flash[:notice] = 'Activity was successfully created.'
        format.html { redirect_to(@activity) }
        format.xml  { render :xml => @activity,
          :status => :created, :location => @activity }
      else
        format.html { render :action => "new" }
        format.xml do
          render :xml => @activity.errors,
          :status => :unprocessable_entity
        end
      end
    end
  end

  def update
    respond_to do |format|
      if @activity.update_attributes(params[:activity])
        expire_action(self.class.index_cache_key(self))
        expire_action(self.class.view_cache_key(self))

        format.html do
          flash[:notice] = 'Activity was successfully updated.'
          redirect_to(@activity)
        end
        format.json { render :text => @activity.to_json(:methods => :tag_list) }
        format.xml  { head :ok }
      else
        format.html { render :action => "edit" }
        format.json { render :json => @activity, :status => 500}
        format.xml  { render :xml => @activity.errors,
          :status => :unprocessable_entity }
      end
    end
  end

  def destroy
    @activity.destroy
    expire_action(self.class.index_cache_key(self))
    expire_action(self.class.view_cache_key(self))

    respond_to do |format|
      format.html { redirect_to(activities_url) }
      format.xml  { head :ok }
    end
  end
end
