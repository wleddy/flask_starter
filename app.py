from flask import Flask, render_template, g, session, url_for, request, redirect, flash, abort
from flask_mail import Mail
from shotglass2 import base_app
from shotglass2.takeabeltof.database import Database
from shotglass2.takeabeltof.utils import send_static_file
from shotglass2.takeabeltof.jinja_filters import register_jinja_filters
from shotglass2.users.models import User,Role,Pref
from shotglass2.users.admin import Admin
import os    

# Create app
# setting static_folder to None allows me to handle loading myself
app = Flask(__name__, instance_relative_config=True,
        static_folder=None)
app.config.from_pyfile('site_settings.py', silent=True)


# work around some web servers that mess up root path
from werkzeug.contrib.fixers import CGIRootFix
if app.config['CGI_ROOT_FIX_APPLY'] == True:
    fixPath = app.config.get("CGI_ROOT_FIX_PATH","/")
    app.wsgi_app = CGIRootFix(app.wsgi_app, app_root=fixPath)

register_jinja_filters(app)


mail = Mail(app)

def init_db(db=None):
    # to support old code
    initalize_all_tables(db)

def initalize_all_tables(db=None):
    """Place code here as needed to initialze all the tables for this site"""
    if not db:
        db = get_db()
        
    base_app.initalize_user_tables(db)
    
    ### setup any other tables you need here....
    
    
def get_db(filespec=None):
    """Return a connection to the database.
    If the db path does not exist, create it and initialize the db"""
    
    if not filespec:
        filespec = app.config['DATABASE_PATH']
        
    initialize = False
    if 'db' not in g:
        # test the path, if not found, create it
        initialize = base_app.make_db_path(filespec)
        
    g.db = Database(filespec).connect()
    if initialize:
        initalize_all_tables(g.db)
            
    return g.db


@app.before_request
def _before():
    # Force all connections to be secure
    if app.config['REQUIRE_SSL'] and not request.is_secure :
        return redirect(request.url.replace("http://", "https://"))

    #ensure that nothing is served from the instance directory
    if 'instance' in request.url:
        abort(404)
        
    #import pdb;pdb.set_trace()
    
    base_app.get_app_config(app)
    #update_config(app)
    
    get_db()
    
    # Is the user signed in?
    g.user = None
    if 'user' in session:
        g.user = session['user']
        base_app.user_setup() # g.admin now holds access rules

@app.teardown_request
def _teardown(exception):
    if 'db' in g:
        g.db.close()


@app.errorhandler(404)
def page_not_found(error):
    return base_app.page_not_found(error)
    # from shotglass2.takeabeltof.utils import handle_request_error
    # handle_request_error(error,request,404)
    # g.title = "Page Not Found"
    # return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    from shotglass2.takeabeltof.utils import handle_request_error
    handle_request_error(error,request,500)
    g.title = "Server Error"
    return render_template('500.html'), 500

#Register the static route
app.add_url_rule('/static/<path:filename>','static',base_app.static)

## Setup the routs for www and users
# or register your own if you prefer
base_app.register_www(app)
base_app.register_users(app)



if __name__ == '__main__':
    
    with app.app_context():
        # create the default database if needed
        initalize_all_tables()
        
    #app.run(host='localhost', port=8000)
    app.run()
    