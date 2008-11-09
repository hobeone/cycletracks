require 'lib/rtcx'

class ActivitiesController < ApplicationController
  before_filter :login_required
  layout "base"

  # GET /activities
  # GET /activities.xml
  def index
    @activities = Activity.find(:all, :order => 'start_time DESC')

    respond_to do |format|
      format.html # index.html.erb
      format.xml  { render :xml => @activities }
    end
  end

  # GET /activities/1
  # GET /activities/1.xml
  def show
    @activity = Activity.find(params[:id])

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

  # GET /activities/new
  # GET /activities/new.xml
  def new
    @activity = Activity.new

    respond_to do |format|
      format.html # new.html.erb
      format.xml  { render :xml => @activity }
    end
  end

  caches_action :show

  def data
    @activity = Activity.find(params[:id])

    data = @activity.time_list.zip(
      @activity.altitude_list,
      @activity.speed_list,
      @activity.cadence_list,
      @activity.distance_list,
      @activity.bpm_list
    )
    activity_data = []
    st = @activity.start_time

    data.each do |t,a,s,c,d,b|
      activity_data << [
        (st + t).strftime('%FT%T'),
        a,
        s,
        c,
        d,
        b
      ].join(',')
    end
    headers["Content-Type"] = "text/plain; charset=utf-8"
    render :text => activity_data.join("\n")
  end

  # POST /activities
  # POST /activities.xml
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
        format.xml  { render :xml => @activity, :status => :created, :location => @activity }
      else
        format.html { render :action => "new" }
        format.xml  { render :xml => @activity.errors, :status => :unprocessable_entity }
      end
    end
  end

  # PUT /activities/1
  # PUT /activities/1.xml
  def update
    @activity = Activity.find(params[:id])

    respond_to do |format|
      if @activity.update_attributes(params[:activity])
        flash[:notice] = 'Activity was successfully updated.'
        format.html { redirect_to(@activity) }
        format.json { render :json => @activity }
        format.xml  { head :ok }
      else
        format.html { render :action => "edit" }
        format.json { render :json => @artist, :status => 500}
        format.xml  { render :xml => @activity.errors, :status => :unprocessable_entity }
      end
    end
  end

  # DELETE /activities/1
  # DELETE /activities/1.xml
  def destroy
    @activity = Activity.find(params[:id])
    @activity.destroy

    respond_to do |format|
      format.html { redirect_to(activities_url) }
      format.xml  { head :ok }
    end
  end
end
