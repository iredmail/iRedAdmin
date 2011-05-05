# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import sys
import ConfigParser

import web
from jinja2 import Environment, FileSystemLoader

# Init settings

# Directory to be used as the Python egg cache directory.
# Note that the directory specified must exist and be writable by the
# user that the daemon process run as.
os.environ['PYTHON_EGG_CACHE'] = '/tmp/.iredadmin-eggs'
os.environ['LC_ALL'] = 'C'

# init settings.ini to a web.storage
rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
settings = ConfigParser.SafeConfigParser()
cfgfile = os.path.join(rootdir, 'settings.ini')
if os.path.exists(cfgfile):
    settings.read(cfgfile)
else:
    sys.exit('Error: No config file found: %s.' % cfgfile)

cfgSections = web.storage(settings._sections)
cfg = web.iredconfig = web.storage()
for k in cfgSections:
    web.iredconfig[k] = web.storage(cfgSections[k])

web.iredconfig['rootdir'] = rootdir

webmaster = cfg.general.get('webmaster', 'root')
backend = cfg.general.get('backend', 'ldap')

# Import urls from backend.
if backend == 'ldap':
    from controllers.ldap.urls import urls as backendUrls
else:
    from controllers.mysql.urls import urls as backendUrls

from controllers.panel.urls import urls as panelUrls

# Merge urls.
urls = panelUrls + backendUrls

# Set debug mode.
if cfg.general.get('debug', 'False').lower() in ['true',]:
    web.config.debug = True
else:
    web.config.debug = False

# Initialize object which used to stored all translations.
cfg.allTranslations = web.storage()

# Get global language setting.
lang = cfg.general.get('lang', 'en_US')

#####################################
# Store all 'true/false' in session.
#
# Get value of 'show_used_quota' in [general].
if backend == 'mysql':
    enableShowUsedQuota = True
else:
    if cfg.general.get('show_used_quota', 'False').lower() in ['true',]:
        enableShowUsedQuota = True
    else:
        enableShowUsedQuota = False

#
# END.
########################

# Set session parameters.
web.config.session_parameters['cookie_name'] = 'iRedAdmin'
web.config.session_parameters['cookie_domain'] = None
web.config.session_parameters['ignore_expiry'] = False
web.config.session_parameters['ignore_change_ip'] = False

# Initialize session object.
db_iredadmin = web.database(
    host=cfg.iredadmin.get('host', 'localhost'),
    port=int(cfg.iredadmin.get('port', '3306')),
    dbn='mysql',
    db=cfg.iredadmin.get('db', 'iredadmin'),
    user=cfg.iredadmin.get('user', 'iredadmin'),
    pw=cfg.iredadmin.get('passwd'),
)

# Store session data in 'iredadmin.sessions'.
sessionStore = web.session.DBStore(db_iredadmin, 'sessions')

# We will use web.admindb in module 'iredutils' later.
web.admindb = db_iredadmin

# Initialize application object.
app = web.application(urls, globals(), autoreload=True)

session = web.session.Session(
    app,
    sessionStore,
    initializer={
        'webmaster': webmaster,
        'username': None,
        'logged': False,
        'failedTimes': 0,   # Integer.
        'lang': lang,
        'pageSizeLimit': 50,

        # Show used quota.
        'enableShowUsedQuota': enableShowUsedQuota,
    }
)

web.config._session = session

import iredutils

# Custom Jinja2 global functions.
render_globals = {
    '_': iredutils.iredGettext,    # Override _() which provided by Jinja2.
    'ctx': web.ctx,                 # Used to get 'homepath'.
    'skin': 'default',              # Used for static files.
    'session': web.config._session,
    'backend': backend,
}

# Custom Jinja filters.
render_filters = {
    'filesizeformat': iredutils.filesizeformat,
    'setDatetimeFormat': iredutils.setDatetimeFormat,
    'getRandomPassword': iredutils.getRandomPassword,
    'getPercentage': iredutils.getPercentage,
    'cutString': iredutils.cutString,
}

# ---- Functions ----
# Hooks.
def hook_lang():
    web.ctx.lang = web.input(lang=None, _method="GET").lang or session.get('lang', 'en_US')

# Define template render.
def render_template(template_name, **context):
    jinja_env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '../templates/default', )),
        extensions=[],
    )
    jinja_env.globals.update(render_globals)
    jinja_env.filters.update(render_filters)

    return jinja_env.get_template(template_name).render(context)

class sessionExpired(web.HTTPError):
    def __init__(self, message):
        message = web.seeother('/login?msg=SESSION_EXPIRED')
        web.HTTPError.__init__(self, '303 See Other', {}, data=message)

# Logger. Logging into SQL database.
def logIntoSQL(msg, admin='', domain='', username='', event='', loglevel='info',):
    try:
        if admin == '':
            admin = session.get('username', '')

        db_iredadmin.insert(
            'log',
            admin=str(admin),
            domain=str(domain),
            username=str(username),
            loglevel=str(loglevel),
            event=str(event),
            msg=str(msg),
            ip=str(session.ip),
        )
    except Exception, e:
        pass

app.add_processor(web.loadhook(hook_lang))

# Mail 500 error to webmaster.
if cfg.general.get('mail_error_to_webmaster', 'False').lower() == 'true':
    app.internalerror = web.emailerrors(webmaster, web.webapi._InternalError,)

# Store objects in 'web' module.
web.app = app
web.render = render_template
web.logger = logIntoSQL
web.session.SessionExpired = sessionExpired
