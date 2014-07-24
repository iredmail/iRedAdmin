# Author: Zhang Huangbin <zhb@iredmail.org>
# Purpose: Add existing virtual mail domains (and their alias domains) to
#          Cluebringer database as internal domains.
#
# Note: iRedAdmin-Pro will do this for you, for example, add new domain or
#       alias domain, delete domain or alias domain. So you don't need to run
#       this frequently. But it's safe to run it as many times as you want, it
#       won't mess up sql records.

# USAGE:
#
#   1: Make sure you have correct database settings in iRedAdmin config file
#      'settings.py' for Cluebringer.
#
#   2: Run this script in command line directly:
#
#       # python /path/to/sync_cluebringer_internal_domains.py
#
# That's all.

import os
import sys
import web

os.environ['LC_ALL'] = 'C'

rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

# Import addition config file of iRedAdmin-Pro: libs/settings.py.
import settings
from tools import ira_tool_lib

web.config.debug = ira_tool_lib.debug
logger = ira_tool_lib.logger

# Check backend
logger.info('Backend: %s' % settings.backend)
if settings.backend in ['ldap', 'mysql']:
    sql_dbn = 'mysql'
elif settings.backend in ['pgsql']:
    sql_dbn = 'postgres'
else:
    sys.exit('Error: Unsupported backend (%s).' % settings.backend)

# Check database name to make sure it's Cluebringer
if settings.policyd_db_name != 'cluebringer':
    sys.exit('Error: not a Cluebringer database.')

logger.info('Query all mail domains (including alias domains).')
all_domains = []
if settings.backend == 'ldap':
    import ldap
    from libs.ldaplib.auth import verify_bind_dn_pw

    # Initialize LDAP connection.
    qr = verify_bind_dn_pw(dn=settings.ldap_bind_dn,
                           password=settings.ldap_bind_password,
                           uri=settings.ldap_uri,
                           close_connection=False)
    if qr[0]:
        ldap_conn = qr[1]

    # Query mail domains
    qr = ldap_conn.search_s(settings.ldap_basedn,
                            ldap.SCOPE_SUBTREE,
                            "(objectClass=mailDomain)",
                            ['domainName', 'domainAliasName'])

    for r in qr:
        entry = r[1]
        all_domains += entry.get('domainName', [])
        all_domains += entry.get('domainAliasName', [])

else:
    conn = web.database(dbn=sql_dbn,
                        host=settings.vmail_db_host,
                        port=int(settings.vmail_db_port),
                        db=settings.vmail_db_name,
                        user=settings.vmail_db_user,
                        pw=settings.vmail_db_password)

    # Get all mail domains
    qr = conn.select('domain', what='domain')
    for r in qr:
        all_domains.append(str(r.domain).lower())

    # Get all alias domains
    qr = conn.select('alias_domain', what='alias_domain')
    for r in qr:
        all_domains.append(str(r.alias_domain).lower())

logger.info('Found %d domain(s).' % len(all_domains))

# Add all mail domains as Cluebringer internal domains.
conn = web.database(dbn=sql_dbn,
                    host=settings.policyd_db_host,
                    port=int(settings.policyd_db_port),
                    db=settings.policyd_db_name,
                    user=settings.policyd_db_user,
                    pw=settings.policyd_db_password)

logger.info('Query ID of Cluebringer policy group "%internal_domains".')
qr = conn.select('policy_groups',
                 what='id',
                 where="""name='internal_domains'""",
                 limit=1)
id_internal_domains = qr[0].id
logger.info('Got ID: %d' % id_internal_domains)

logger.info('Syncing...')
for domain in all_domains:
    value = {'policygroupid': id_internal_domains,
             'member': '@' + domain,
             'disabled': 0}

    try:
        conn.insert('policy_group_members', **value)
        logger.info('[%s] Successfully added.' % domain)
    except Exception, e:
        if e[0] == 1062:
            logger.info('[%s] SKIP, already exists.' % domain)
        else:
            logger.error('< ERROR > [%s] %s' % (domain, str(e)))

logger.info('DONE')
