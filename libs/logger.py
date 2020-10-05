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

# Set log level.
_log_level = getattr(logging, str(settings.SYSLOG_LOG_LEVEL).upper())
logger.setLevel(_log_level)

# Log format
_formatter = logging.Formatter("%(name)s %(message)s (%(pathname)s, line %(lineno)d)")
_facility = getattr(SysLogHandler, "LOG_" + settings.SYSLOG_FACILITY.upper())

if settings.SYSLOG_SERVER.startswith("/"):
    # Log to a local socket
    _handler = SysLogHandler(address=settings.SYSLOG_SERVER, facility=_facility)
else:
    # Log to a network address
    _server = (settings.SYSLOG_SERVER, settings.SYSLOG_PORT)
    _handler = SysLogHandler(address=_server, facility=_facility)

_handler.setFormatter(_formatter)
logger.addHandler(_handler)


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
