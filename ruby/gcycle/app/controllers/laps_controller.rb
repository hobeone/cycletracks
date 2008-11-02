class LapsController < ApplicationController
  before_filter :load_activity

  def load_activity
    @activity = Activity.find(params[:activity_id])
  end

  # GET /laps
  # GET /laps.xml
  def index
    @laps = Lap.find(:all)

    respond_to do |format|
      format.html # index.html.erb
      format.xml  { render :xml => @laps }
    end
  end

  # GET /laps/1
  # GET /laps/1.xml
  def show
    @lap = @activity.laps.find(params[:id])

    respond_to do |format|
      format.html # show.html.erb
      format.xml  { render :xml => @lap }
    end
  end

  # GET /laps/new
  # GET /laps/new.xml
  def new
    @lap = @activity.laps.build

    respond_to do |format|
      format.html # new.html.erb
      format.xml  { render :xml => @lap }
    end
  end

  # GET /laps/1/edit
  def edit
    @lap = @activity.laps.find(params[:id])
  end

  # POST /laps
  # POST /laps.xml
  def create
    @lap = @activity.laps.build(params[:lap])

    respond_to do |format|
      if @lap.save
        flash[:notice] = 'Lap was successfully created.'
        format.html { redirect_to([@activity, @lap]) }
        format.xml  { render :xml => @lap, :status => :created, :location => @lap }
      else
        format.html { render :action => "new" }
        format.xml  { render :xml => @lap.errors, :status => :unprocessable_entity }
      end
    end
  end

  # PUT /laps/1
  # PUT /laps/1.xml
  def update
    @lap = @activity.laps.find(params[:id])

    respond_to do |format|
      if @lap.update_attributes(params[:lap])
        flash[:notice] = 'Lap was successfully updated.'
        format.html { redirect_to([@activity, @lap]) }
        format.xml  { head :ok }
      else
        format.html { render :action => "edit" }
        format.xml  { render :xml => @lap.errors, :status => :unprocessable_entity }
      end
    end
  end

  # DELETE /laps/1
  # DELETE /laps/1.xml
  def destroy
    @lap = @activity.laps.find(params[:id])
    @lap.destroy

    respond_to do |format|
      format.html { redirect_to(activity_laps_url(@activity)) }
      format.xml  { head :ok }
    end
  end
end
