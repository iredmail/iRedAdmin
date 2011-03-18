# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import web

from libs import iredutils
from libs.mysql import core

class Utils(core.MySQLWrap):

    def isDomainExists(self, domain):
        if not iredutils.isDomain(domain):
            return True

        try:
            result = self.conn.select(
                'domain',
                what='domain',
                where='domain = %s' % web.sqlquote(domain),
                limit=1,
            )

            if len(result) > 0:
                # Exists.
                return True

            result = self.conn.select(
                'alias_domain',
                what='alias_domain',
                where='alias_domain = %s' % web.sqlquote(domain),
                limit=1,
            )

            if len(result) > 0:
                # Alias domain exists.
                return True
            else:
                return False
        except:
            # Return True as exist to not allow to create new domain/account.
            return True

    def isAdminExists(self, mail):
        # Return True if account is invalid or exist.
        mail = str(mail)
        if not iredutils.isEmail(mail):
            return True

        try:
            result = self.conn.select(
                'admin',
                what='username',
                where='username = %s' % web.sqlquote(mail),
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
    def isEmailExists(self, mail):
        # Return True if account is invalid or exist.
        self.mail = web.safestr(mail)

        if not iredutils.isEmail(mail):
            return True

        self.sqlMail = web.sqlquote(self.mail)

        try:
            resultOfAlias = self.conn.select(
                'alias',
                what='address',
                where='address=%s' % self.sqlMail,
                limit=1,
            )

            resultOfMailbox = self.conn.select(
                'mailbox',
                what='username',
                where='username=%s' % self.sqlMail,
                limit=1,
            )

            if len(resultOfAlias) == 1 or len(resultOfMailbox) == 1:
                return True
            else:
                return False

        except Exception, e:
            return True

