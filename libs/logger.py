import sys
import logging
import traceback
from logging.handlers import SysLogHandler

import web
from libs import iredutils
import settings

session = web.config.get("_session")

# Set application name.
logger = logging.getLogger("iredadmin")

# Log format
_formatter = logging.Formatter("%(name)s %(message)s (%(pathname)s, line %(lineno)d)")

# Set default log level.
_default_log_level = getattr(logging, str(settings.DEFAULT_LOG_LEVEL).upper())
logger.setLevel(_default_log_level)

if settings.LOG_TO_SYSLOG:
    _syslog_facility = getattr(SysLogHandler, "LOG_" + settings.SYSLOG_FACILITY.upper())

    if settings.SYSLOG_SERVER.startswith("/"):
        # Log to a local socket
        _syslog_handler = SysLogHandler(address=settings.SYSLOG_SERVER, facility=_syslog_facility)
    else:
        # Log to a network address
        _server = (settings.SYSLOG_SERVER, settings.SYSLOG_PORT)
        _syslog_handler = SysLogHandler(address=_server, facility=_syslog_facility)

    _syslog_handler.setFormatter(_formatter)
    _syslog_handler.setLevel(getattr(logging, str(settings.SYSLOG_LOG_LEVEL).upper()))
    logger.addHandler(_syslog_handler)

if settings.LOG_TO_STDOUT:
    _stdout_handler = logging.StreamHandler(sys.stdout)
    _stdout_handler.setFormatter(_formatter)
    _stdout_handler.setLevel(getattr(logging, str(settings.STDOUT_LOG_LEVEL).upper()))
    logger.addHandler(_stdout_handler)

def log_traceback():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    msg = traceback.format_exception(exc_type, exc_value, exc_traceback)
    logger.error(msg)


def log_activity(msg, admin="", domain="", username="", event="", loglevel="info"):
    try:
        if not admin:
            admin = session.get("username")

        msg = str(msg)

        # Prepend '[API]' in log message
        try:
            if web.ctx.fullpath.startswith("/api/"):
                msg = "[API] " + msg
        except:
            pass

        web.conn_iredadmin.insert(
            "log",
            admin=str(admin),
            domain=str(domain),
            username=str(username),
            loglevel=str(loglevel),
            event=str(event),
            msg=msg,
            ip=str(session.ip),
            timestamp=iredutils.get_gmttime(),
        )
    except:
        pass

    return None
