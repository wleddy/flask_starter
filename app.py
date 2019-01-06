from flask import Flask, render_template, g, session, url_for, request, redirect, flash, abort
from flask_mail import Mail
from shotglass2 import shotglass
from shotglass2.takeabeltof.database import Database
from shotglass2.takeabeltof.utils import send_static_file
from shotglass2.takeabeltof.jinja_filters import register_jinja_filters
from shotglass2.users.admin import Admin

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
        
    shotglass.initalize_user_tables(db)
    
    ### setup any other tables you need here....
    
    
def get_db(filespec=None):
    """Return a connection to the database.
    If the db path does not exist, create it and initialize the db"""
    
    if not filespec:
        filespec = app.config['DATABASE_PATH']
        
    # This is probobly a good place to change the
    # filespec if you want to use a different database
    # for the current request.
    
        
    initialize = False
    if 'db' not in g:
        # test the path, if not found, create it
        initialize = shotglass.make_db_path(filespec)
        
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
    
    shotglass.get_app_config(app)
    
    get_db()
    
    # Is the user signed in?
    g.user = None
    if 'user' in session:
        g.user = session['user']
        
        
    g.admin = Admin(g.db) # This is where user access rules are stored
    shotglass.user_setup() # g.admin now holds access rules Users, Prefs and Roles

@app.teardown_request
def _teardown(exception):
    if 'db' in g:
        g.db.close()


@app.errorhandler(404)
def page_not_found(error):
    return shotglass.page_not_found(error)

@app.errorhandler(500)
def server_error(error):
    return shotglass.server_error(error)
    

#Register the static route
app.add_url_rule('/static/<path:filename>','static',shotglass.static)

def wack():
    g.suppress_page_header = True
    return render_template('index.html',rendered_html="<h2>You're a wackadoodle!</h2>")

def setup_blueprints():
    ## Setup the routes for users
    shotglass.register_users(app)

    # Use the default www.routes...
    #shotglass.register_www(app)

    # or cherry pick the ones you want and provide
    # your own for the rest

    ## Define your functions first (but not here... )
    #def wack():
    #    g.suppress_page_header = True
    #    return render_template('markdown.html',rendered_html="<h2>You're a wackadoodle!</h2>")

    #Override the routes your interested in
    from shotglass2.www.views import home
    home_mod = home.mod 
    routes = home.get_default_routes()
    # The 4th param is usulally {} or {'methods':['GET','PUT',]}
    routes['/'] = ('/','home',wack,{}) # was ('/','home',home,**options)
    for key, value in routes.items():
        home_mod.add_url_rule(value[0],value[1],value[2],**value[3])
    
    # Then register them on the app
    app.register_blueprint(home_mod)
    

# app.add_url_rule('/','www.home',home)
# #import pdb;pdb.set_trace()
#app.url_map

if __name__ == '__main__':
    
    with app.app_context():
        # create the default database if needed
        initalize_all_tables()
        setup_blueprints()
        
    #app.run(host='localhost', port=8000)
    app.run()
    