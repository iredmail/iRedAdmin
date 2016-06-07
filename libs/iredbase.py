# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import sys
import gettext

import web
from jinja2 import Environment, FileSystemLoader

# Init settings

# Directory to be used as the Python egg cache directory.
# Note that the directory specified must exist and be writable by the
# user that the daemon process run as.
os.environ['PYTHON_EGG_CACHE'] = '/tmp/.iredadmin-eggs'
os.environ['LC_ALL'] = 'C'

import iredutils
import settings
from ireddate import convert_utc_to_timezone

# Set debug mode.
web.config.debug = settings.DEBUG

# Set session parameters.
web.config.session_parameters['cookie_name'] = 'iRedAdmin'
web.config.session_parameters['cookie_domain'] = None
web.config.session_parameters['ignore_expiry'] = False
web.config.session_parameters['ignore_change_ip'] = False
web.config.session_parameters['timeout'] = settings.SESSION_TIMEOUT

# Initialize session object.
session_dbn = 'mysql'
if settings.backend in ['pgsql', ]:
    session_dbn = 'postgres'

db_iredadmin = web.database(
    host=settings.iredadmin_db_host,
    port=int(settings.iredadmin_db_port),
    dbn=session_dbn,
    db=settings.iredadmin_db_name,
    user=settings.iredadmin_db_user,
    pw=settings.iredadmin_db_password,
)
db_iredadmin.supports_multiple_insert = True

# Store session data in 'iredadmin.sessions'.
sessionStore = web.session.DBStore(db_iredadmin, 'sessions')

# We will use web.admindb in module 'iredutils' later.
web.admindb = db_iredadmin

# URL handlers.
# Import backend related urls.
if settings.backend == 'ldap':
    from controllers.ldap.urls import urls as backendUrls
elif settings.backend == 'mysql':
    from controllers.mysql.urls import urls as backendUrls
elif settings.backend == 'pgsql':
    from controllers.pgsql.urls import urls as backendUrls
else:
    backendUrls = []

urls = backendUrls

from controllers.panel.urls import urls as panelUrls
urls += panelUrls

# Initialize application object.
app = web.application(urls, globals(),)

session = web.session.Session(
    app,
    sessionStore,
    initializer={
        'webmaster': settings.webmaster,
        'username': None,
        'logged': False,
        'failed_times': 0,   # Integer.
        'lang': settings.default_language,
        'is_global_admin': False,
        'default_mta_transport': settings.default_mta_transport,

        # Store password in plain text.
        'store_password_in_plain_text': settings.STORE_PASSWORD_IN_PLAIN_TEXT,

        # Amavisd related features.
        'amavisd_enable_quarantine': settings.amavisd_enable_quarantine,
    }
)

web.config._session = session


# Generate CSRF token and store it in session.
def csrf_token():
    if 'csrf_token' not in session.keys():
        session['csrf_token'] = iredutils.generate_random_strings(32)

    return session['csrf_token']

# Hooks.
def hook_lang():
    web.ctx.lang = web.input(lang=None, _method="GET").lang or session.get('lang', 'en_US')

# Initialize object which used to stored all translations.
all_translations = {'en_US': gettext.NullTranslations()}

# Translations
def ired_gettext(string):
    """Translate a given string to the language of the application."""
    lang = session.lang

    if lang in all_translations:
        translation = all_translations[lang]
    else:
        try:
            # Store new translation
            translation = gettext.translation(
                'iredadmin',
                os.path.abspath(os.path.dirname(__file__)) + '/../i18n',
                languages=[lang])
            all_translations[lang] = translation
        except:
            translation = all_translations['en_US']

    return translation.ugettext(string)


# Define template render.
def render_template(template_name, **context):
    jinja_env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                             '../templates/default', )),
        extensions=[],
    )
    jinja_env.globals.update({
        '_': ired_gettext,  # Override _() which provided by Jinja2.
        'ctx': web.ctx,     # Used to get 'homepath'.
        'skin': 'default',  # Used for static files.
        'session': web.config._session,
        'backend': settings.backend,
        'csrf_token': csrf_token,
        'pageSizeLimit': settings.PAGE_SIZE_LIMIT,
        # Brand logo, name, description
        'brand_logo': settings.BRAND_LOGO,
        'brand_name': settings.BRAND_NAME,
        'brand_desc': settings.BRAND_DESC,
    })

    jinja_env.filters.update({
        'filesizeformat': iredutils.filesizeformat,
        'set_datetime_format': iredutils.set_datetime_format,
        'generate_random_strings': iredutils.generate_random_strings,
        'cut_string': iredutils.cut_string,
        'convert_utc_to_timezone': convert_utc_to_timezone,
    })

    web.header('Content-Type', 'text/html')
    return jinja_env.get_template(template_name).render(context)


class SessionExpired(web.HTTPError):
    def __init__(self, message):
        message = web.seeother('/login?msg=SESSION_EXPIRED')
        web.HTTPError.__init__(self, '303 See Other', {}, data=message)


# Logger. Logging into SQL database.
def log_into_sql(msg,
                 admin='',
                 domain='',
                 username='',
                 event='',
                 loglevel='info'):
    try:
        if not admin:
            admin = session.get('username')

        db_iredadmin.insert(
            'log',
            admin=str(admin),
            domain=str(domain),
            username=str(username),
            loglevel=str(loglevel),
            event=str(event),
            msg=str(msg),
            ip=str(session.ip),
            timestamp=iredutils.get_gmttime(),
        )
    except Exception:
        pass

    return None


# Log error message. default log to sys.stderr.
def log_error(*args):
    for s in args:
        try:
            print >> sys.stderr, web.safestr(s)
        except Exception, e:
            print >> sys.stderr, e

# Load hooks
app.add_processor(web.loadhook(hook_lang))

# Mail 500 error to webmaster.
if settings.MAIL_ERROR_TO_WEBMASTER:
    app.internalerror = web.emailerrors(settings.webmaster, web.webapi._InternalError)

# Store objects in 'web' module.
web.app = app
web.render = render_template
web.logger = log_into_sql
web.log_error = log_error
web.session.SessionExpired = SessionExpired
