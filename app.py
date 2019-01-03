from flask import Flask, render_template, g, session, url_for, request, redirect, flash, abort
from flask_mail import Mail
from shotglass2.base_app import get_app_config, make_db_path, register_www, register_users, user_setup
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
        
    from shotglass2.users.models import init_db as users_init_db 
    users_init_db(db)
    

def update_config_for_host():
    # update settings for the requested host
    #import pdb;pdb.set_trace()
    
    # if there is no request this function will error out
    # check to see if the property we need is available
    request_in_flight = True
    try:
        request.url
    except:
        request_in_flight = False
        
    if request_in_flight and "SUB_DOMAIN_SETTINGS" in app.config and len(app.config["SUB_DOMAIN_SETTINGS"]) > 0:
        try:
            server = None
            for value in app.config['SUB_DOMAIN_SETTINGS']:
                if value.get('host_name') == request.host:
                    server = value
                    break

            if not server:
                #did not find a server to match, use default
                raise ValueError
            
            for key, value in server.items():
                app.config[key.upper()] = value
            
            # refresh mail since settings changed
            mail = Mail(app)
            
        except:
            # Will use the default settings
            if app.config['DEBUG']:
                #raise ValueError("SUB_DOMAIN_SETTINGS could not be determined")
                flash("Using Default SUB_DOMAIN_SETTINGS")
    
        
# def get_app_config():
#     """Returns a copy of the current app.config.
#     This makes it possible for other modules to get access to the config
#     with the values as updated for the current host.
#     Import this method rather than importing app
#     """
#     import pdb;pdb.set_trace()
#     update_config(app)
#     return app.config

    
def get_db(filespec=None):
    """Return a connection to the database.
    If the db path does not exist, create it and initialize the db"""
    
    if not filespec:
        filespec = app.config['DATABASE_PATH']
        
    initialize = False
    if 'db' not in g:
        # test the path, if not found, create it
        initialize = make_db_path(filespec)
        
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
    
    get_app_config(app)
    #update_config(app)
    
    get_db()
    
    # Is the user signed in?
    g.user = None
    if 'user' in session:
        g.user = session['user']
        user_setup()

@app.teardown_request
def _teardown(exception):
    if 'db' in g:
        g.db.close()


@app.errorhandler(404)
def page_not_found(error):
    from shotglass2.takeabeltof.utils import handle_request_error
    handle_request_error(error,request,404)
    g.title = "Page Not Found"
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    from shotglass2.takeabeltof.utils import handle_request_error
    handle_request_error(error,request,500)
    g.title = "Server Error"
    return render_template('500.html'), 500

@app.route('/static/<path:filename>')
def static(filename):
    """This takes full responsibility for loading static content"""
        
    local_path = []
    if app.config.get('LOCAL_STATIC_DIRS'):
        local_path = app.config['LOCAL_STATIC_DIRS'] 
    if app.config.get('STATIC_DIRS'):
        #append STATIC_DIRS to LOCAL_STATIC_DIRS
        for folder in app.config.get('STATIC_DIRS'):
            local_path.append(folder)
        
    return send_static_file(filename,path_list=local_path)

## Setup the routs for www and users
# or register your own if you prefer
register_www(app)
register_users(app)

if __name__ == '__main__':
    
    with app.app_context():
        # create the default database if needed
        initalize_all_tables()
        
    #app.run(host='localhost', port=8000)
    app.run()
    