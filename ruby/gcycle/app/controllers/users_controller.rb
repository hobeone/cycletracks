class UsersController < ApplicationController
  before_filter :login_required, :only => [ :update, :show]
  before_filter :authorize_update, :only => [ :update, :show ]
  layout "base"

  def authorize_update
    return true if @current_user.admin?
    return true if params[:id] == @current_user.id
    return false
  end

  def show
    @user = User.find(params[:id])
  end

  def new
    @user = User.new
  end

  def create
    logout_keeping_session!
    @user = User.new(params[:user])
    success = @user && @user.save
    if success && @user.errors.empty?
      # Protects against session fixation attacks, causes request forgery
      # protection if visitor resubmits an earlier form using back
      # button. Uncomment if you understand the tradeoffs.
      # reset session
      self.current_user = @user # !! now logged in
      redirect_back_or_default('/')
      flash[:notice] = "Thanks for signing up!  We're sending you an email with your activation code."
    else
      flash[:error]  = "We couldn't set up that account, sorry.  Please try again, or contact an admin (link is above)."
      render :action => 'new'
    end
  end

  def update
    @user = User.find(params[:id])

    respond_to do |format|
      if @user.update_attributes(params[:user])
        flash[:notice] = 'User was successfully updated.'
        format.html { redirect_to('/') }
        format.json { render :json => @user }
        format.xml  { head :ok }
      else
        format.html { render :action => "edit" }
        format.json { render :json => @user, :status => 500}
        format.xml  { render :xml => @user.errors,
          :status => :unprocessable_entity }
      end
    end
  end

end
