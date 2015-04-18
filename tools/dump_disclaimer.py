#!/usr/bin/env python
# encoding: utf-8

# Author:   Zhang Huangbin <zhb@iredmail.org>
# Updated:  2012.07.01
# Purpose:  Dump disclaimer text from OpenLDAP directory server or SQL servers.
# Requirements: iRedMail-0.5.0 or later releases
#
# Shipped within iRedAdmin-Pro: http://www.iredmail.org/admin_panel.html

# USAGE:
#
#   - Make sure you have correct backend related settings in iRedAdmin config
#     file, settings.ini.
#
#   - Test this script in command line directly, make sure no errors in output
#     message.
#
#       # python /path/to/dump_disclaimer.py /etc/postfix/disclaimer/
#
#   - Setup a cron job to execute this script daily. For example: execute
#     this script at 2:01AM every day.
#
#       1  2   *   *   *   python /path/to/dump_disclaimer.py /etc/postfix/disclaimer/
#
# That's all.

import os
import sys
import web

web.config.debug = False

# Directory used to store disclaimer files.
# Default directory is /etc/postfix/disclaimer/.
# Default disclaimer file name is [domain_name].txt
if len(sys.argv) != 2:
    sys.exit('Error: Please specify a directory used to store disclaimer, default is /etc/postfix/disclaimer/')
else:
    DISCLAIMER_DIR = sys.argv[1]
    DISCLAIMER_FILE_EXT = '.txt'

os.environ['LC_ALL'] = 'C'
rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'
sys.path.insert(0, rootdir)

import settings
from tools import ira_tool_lib
logger = ira_tool_lib.logger


def dump_from_ldap():
    """Dump disclaimer text from LDAP server."""

    try:
        import ldap
    except ImportError:
        logger.info("Error: You don't have package 'python-ldap' installed, Please install it first.")
        sys.exit()

    logger.info('Connecting to LDAP server')
    conn = ldap.initialize(settings.ldap_uri, trace_level=0)
    conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

    logger.info('Binding with dn: %s' % settings.ldap_basedn)
    conn.bind_s(settings.ldap_bind_dn, settings.ldap_bind_password)

    # Search and get disclaimer.
    logger.info('Searching accounts which have disclaimer configured')
    qr = conn.search_s(
        settings.ldap_basedn,
        ldap.SCOPE_ONELEVEL,
        '(objectclass=maildomain)',
        ['domainName', 'disclaimer'],
    )

    logger.info('Dumping ...')
    # Dump disclaimer for every domain.
    counter = 0
    for (dn, entry) in qr:
        # Get domain name.
        domainName = entry['domainName'][0]

        # Set file name.
        disclaimer_file = os.path.join(DISCLAIMER_DIR, domainName)
        vars = {'domain': domainName, 'dest_file': disclaimer_file}

        if 'disclaimer' in entry:
            counter += 1
            # Dump disclaimer text.
            try:
                # Write plain text
                f = open(disclaimer_file + '.txt', 'w')
                f.write('\n' + entry['disclaimer'][0] + '\n')
                f.close()

                # Write html format
                f = open(disclaimer_file + '.html', 'w')
                f.write('<div>' + entry['disclaimer'][0] + '</div>')
                f.close()

                logger.info('+ %(domain)s -> %(dest_file)s.{txt,html}' % vars)
            except Exception, e:
                logger.info('[ERROR] (%s): %s ...' % (domainName, str(e)))
        else:
            # Remove old disclaimer file if no disclaimer setting
            try:
                for f in [disclaimer_file + '.txt', disclaimer_file + '.html']:
                    if os.path.isfile(f):
                        os.remove(f)
                logger.info("- %(domain)s -> [REMOVE] Unused disclaimer: %(dest_file)s.{txt,html}." % vars)
            except OSError:
                # File not exist.
                logger.info("= %(domain)s -> [SKIP] No disciaimer configured." % vars)
            except Exception, e:
                # Other errors.
                logger.info("[ERROR] %s: %s." % (domainName, str(e)))

    logger.info('Total %d domains.' % counter)

    # Close connection.
    conn.unbind()
    logger.info('Connection closed.')


def dump_from_mysql():
    """Dump disclaimer text from MySQL server."""
    logger.info('Connecting MySQL server ...')
    conn = web.database(dbn='mysql',
                        host=settings.vmail_db_host,
                        port=int(settings.vmail_db_port),
                        db=settings.vmail_db_name,
                        user=settings.vmail_db_user,
                        pw=settings.vmail_db_password)

    # Search and get disclaimer.
    logger.info('Get disclaimer text ...')
    qr = conn.select('domain', what='domain,disclaimer')

    # Dump disclaimer for every domain.
    logger.info('Dumping...')
    for r in qr:
        domain = str(r.domain).lower()
        # Set file name.
        disclaimer_file = DISCLAIMER_DIR + '/' + domain + DISCLAIMER_FILE_EXT

        if r.disclaimer:
            # Dump disclaimer text.
            try:
                f = open(disclaimer_file, 'w')
                #f.write( entry['disclaimer'][0].decode('utf-8') )
                f.write('\n' + r.disclaimer + '\n')  # .decode('utf-8') )
                f.close()

                logger.info('Dump disclaimer text to file: %s.' % disclaimer_file)
            except Exception, e:
                logger.info('SKIP (%s): %s.' % (domain, str(e)))
        else:
            # Remove old disclaimer file if no disclaimer setting in LDAP.
            try:
                os.remove(disclaimer_file)
                logger.info("Remove old disclaimer file: %s." % (disclaimer_file))
            except OSError:
                # File not exist.
                pass
            except Exception, e:
                # Other errors.
                logger.info("Error while deleting (%s): %s." % (disclaimer_file, str(e)))

    logger.info('Completed.')


if settings.backend == 'ldap':
    dump_from_ldap()
elif settings.backend == 'mysql':
    dump_from_mysql()
#elif settings.backend == 'pgsql':
#    dump_from_pgsql()
