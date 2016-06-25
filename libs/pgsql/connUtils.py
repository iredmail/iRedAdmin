# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web

from libs import iredutils
from libs.pgsql import core

session = web.config.get('_session')


class Utils(core.PGSQLWrap):

    def is_domain_exists(self, domain):
        # Return True if account is invalid or exist.
        domain = str(domain)
        if not iredutils.is_domain(domain):
            return True

        sql_vars = {'domain': domain, }
        try:
            result = self.conn.select(
                'domain',
                vars=sql_vars,
                what='domain',
                where='domain=$domain',
                limit=1,
            )

            if len(result) > 0:
                # Exists.
                return True

            result = self.conn.select(
                'alias_domain',
                vars=sql_vars,
                what='alias_domain',
                where='alias_domain=$domain',
                limit=1,
            )

            if len(result) > 0:
                # Alias domain exists.
                return True
            else:
                return False
        except Exception:
            # Return True as exist to not allow to create new domain/account.
            return True

    def isAdminExists(self, mail):
        # Return True if account is invalid or exist.
        mail = str(mail)
        if not iredutils.is_email(mail):
            return True

        try:
            result = self.conn.select(
                'admin',
                vars={'username': mail, },
                what='username',
                where='username=$username',
                limit=1,
            )

            if len(result) > 0:
                # Exists.
                return True
            else:
                return False
        except:
            # Return True as exist to not allow to create new domain/account.
            return True

    # Check whether account exist or not.
    def is_email_exists(self, mail):
        # Return True if account is invalid or exist.
        mail = web.safestr(mail)

        if not iredutils.is_email(mail):
            return True

        sql_vars = {'email': mail, }

        try:
            resultOfMailbox = self.conn.select(
                'mailbox',
                vars=sql_vars,
                what='username',
                where='username=$email',
                limit=1,
            )

            resultOfAlias = self.conn.select(
                'alias',
                vars=sql_vars,
                what='address',
                where='address=$email',
                limit=1,
            )

            if resultOfMailbox or resultOfAlias:
                return True
            else:
                return False

        except Exception:
            return True

    # Get domains under control.
    def getManagedDomains(self, admin, domainNameOnly=False, listedOnly=False,):
        admin = web.safestr(admin)

        if not iredutils.is_email(admin):
            return (False, 'INCORRECT_USERNAME')

        sql_left_join = ''
        if listedOnly is False:
            sql_left_join = """OR domain_admins.domain='ALL'"""

        try:
            result = self.conn.query(
                """
                SELECT domain.domain
                FROM domain
                LEFT JOIN domain_admins ON (domain.domain=domain_admins.domain %s)
                WHERE domain_admins.username=$admin
                ORDER BY domain_admins.domain
                """ % (sql_left_join),
                vars={'admin': admin, },
            )

            if domainNameOnly is True:
                domains = []
                for i in result:
                    if iredutils.is_domain(i.domain):
                        domains += [str(i.domain).lower()]

                return (True, domains)
            else:
                return (True, list(result))
        except Exception, e:
            return (False, str(e))
