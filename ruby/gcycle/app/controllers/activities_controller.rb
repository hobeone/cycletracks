require 'lib/rtcx'

class ActivitiesController < ApplicationController
  include ApplicationHelper

  before_filter :login_required
  before_filter :authorize_index_view, :only => [ :index ]
  before_filter :authorize_views_and_mods, :only => [:show, :data,
    :update, :destroy]
  layout "base"

  def authorize_index_view
    return true if @current_user.admin?
    return true if params[:user_id] == @current_user.id.to_s
    return true if params[:user_id].nil?
    flash[:error] = 'Access to that resource denied'
    redirect_to '/'
  end

  def authorize_views_and_mods
    return true if @current_user.admin?
    @activity = Activity.find(params[:id])
    return true if @activity.user = @current_user
    if (request.xhr?)
      format.json { render :json => @activity, :status => 500}
    end

    flash[:error] = 'Access to that resource denied'
    redirect_to '/'
  end

  def index
    Activity.send(:with_scope,
                  :find => {
      :conditions => ['user_id = ?', @current_user.id]}) do
      if Activity.count > 0
        if stale?(:last_modified => Activity.maximum(:updated_at).utc,
                  :etag => [@current_user]
                 )
          @activities = Activity.find(:all,
                                      :order => 'start_time DESC',
                                      :include => :tags)
          respond_to do |format|
            format.html # index.html.erb
            format.xml  { render :xml => @activities }
          end
        end
      else
        @activities = []
      end
    end
  end

  caches_action :tags
  def tags
    Activity.send(:with_scope,
                  :find => {
      :conditions => ['user_id = ? or public = ?', @current_user.id, true]}) do
      tags = params[:tags]
      @activities = Activity.find_tagged_with(tags, :match_all => true)
    end
    render :action => "index"
  end

  caches_action :show
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
        format.html # show.html.erb
        format.xml  { render :xml => @activity }
      end
    end
  end

  def mps_to_prefered_speed(mps)
    dist = mps * 3.6
    dist = km_to_miles(dist) unless use_metric
    return dist
  end

  caches_action :data
  def data
    data = @activity.time_list.zip(
      @activity.altitude_list,
      @activity.speed_list,
      @activity.cadence_list,
      @activity.distance_list,
      @activity.bpm_list
    )
    activity_data = []
    st = @activity.start_time

    data.each do |time,alt,speed,cad,dist,bpm|
      activity_data << [
        (st + time).strftime('%FT%T'),
        meters_to_prefered_distance(alt),
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
        flash[:notice] = 'Activity was successfully created.'
        format.html { redirect_to(@activity) }
        format.xml  { render :xml => @activity,
          :status => :created, :location => @activity }
      else
        format.html { render :action => "new" }
        format.xml  { render :xml => @activity.errors,
          :status => :unprocessable_entity }
      end
    end
  end

  def update
    respond_to do |format|
      if @activity.update_attributes(params[:activity])
        expire_action :action => :show
        expire_action :action => :tags

        format.html {
          flash[:notice] = 'Activity was successfully updated.'
          redirect_to(@activity)
        }
        format.json { render :text => @activity.to_json(:methods => :tag_list) }
        format.xml  { head :ok }
      else
        format.html { render :action => "edit" }
        format.json { render :json => @activity, :status => 500}
        format.xml  { render :xml => @activity.errors, :status => :unprocessable_entity }
      end
    end
  end

  def destroy
    @activity.destroy
    expire_action :action => :index
    expire_action :action => :show

    respond_to do |format|
      format.html { redirect_to(activities_url) }
      format.xml  { head :ok }
    end
  end
end
