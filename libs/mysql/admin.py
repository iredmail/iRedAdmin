# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import sys
import types
import web
from libs import iredutils
from libs.mysql import core, decorators, connUtils

cfg = web.iredconfig
session = web.config.get('_session')


class Admin(core.MySQLWrap):
    def __del__(self):
        pass

    def getAllAdmins(self, columns=[]):
        """Get all admins. Return (True, [records])."""
        try:
            if columns:
                result = self.conn.select('admin', what=','.join(columns),)
            else:
                result = self.conn.select('admin')

            return (True, list(result))
        except Exception, e:
            return (False, str(e))

    def getAllGlobalAdmins(self):
        try:
            qr = self.conn.select('domain_admins',
                                  what='username,domain',
                                  where="domain='ALL'",
                                 )
            result = []
            for r in qr:
                result += [str(r.username).lower()]
            return (True, result)
        except Exception, e:
            return (False, str(e))

    @decorators.require_global_admin
    def listAccounts(self, cur_page=1,):
        '''List all admins.'''
        # Pre-defined.
        self.total = 0

        # Get current page.
        cur_page = int(cur_page)

        self.sql_limit = ''
        if cur_page > 0:
            self.sql_limit = 'LIMIT %d OFFSET %d' % (
                session['pageSizeLimit'],
                (cur_page-1)*session['pageSizeLimit'],
            )

        try:
            result = self.conn.select('admin', what='COUNT(*) AS total')
            if len(result) > 0:
                self.total = result[0].total or 0
        except Exception, e:
            pass

        try:
            result = self.conn.query(
                """
                SELECT
                    name, username, language, created, active
                FROM admin
                ORDER BY username ASC
                %s
                """ % (self.sql_limit)
            )
            #result = self.conn.select(
            #    'admin',
            #    what='name, username, language, created, active',
            #    order='username ASC',
            #    limit=session['pageSizeLimit'],
            #    offset=(cur_page-1)*session['pageSizeLimit'],
            #)
            return (True, self.total, list(result))
        except Exception, e:
            return (False, str(e))


    # Get domains under control.
    def getManagedDomains(self, admin, domainNameOnly=False, listedOnly=False,):
        self.admin = web.safestr(admin)

        if not iredutils.isEmail(self.admin):
            return (False, 'INCORRECT_USERNAME')

        self.sql_where = ''
        self.sql_left_join = ''
        if listedOnly is True:
            self.sql_where = 'AND domain_admins.username=%s' % web.sqlquote(self.admin)
        else:
            self.sql_left_join = 'OR domain_admins.domain="ALL"' % web.sqlquote(self.admin)

        try:
            result = self.conn.query(
                """
                SELECT domain.domain
                FROM domain
                LEFT JOIN domain_admins ON (domain.domain=domain_admins.domain %s)
                WHERE domain_admins.username=%s %s
                ORDER BY domain_admins.domain
                """ % (self.sql_left_join, web.sqlquote(self.admin), self.sql_where)
            )

            if domainNameOnly is True:
                domains = []
                for i in result:
                    if iredutils.isDomain(i.domain):
                        domains += [str(i.domain).lower()]

                return (True, domains)
            else:
                return (True, list(result))
        except Exception, e:
            return (False, str(e))

    # Get number of domains under control.
    def getNumberOfManagedAccounts(self, admin=None, accountType='domain', domains=[],):
        if admin is None:
            self.admin = session.get('username')
        else:
            self.admin = str(admin)

        if not iredutils.isEmail(self.admin):
            return 0

        self.domains = []
        if len(domains) > 0:
            self.domains = [str(d).lower() for d in domains if iredutils.isDomain(d)]
        else:
            qr = self.getManagedDomains(admin=self.admin, domainNameOnly=True)
            if qr[0] is True:
                self.domains = qr[1]
            else:
                self.domains = []

        if accountType == 'domain':
            try:
                if self.isGlobalAdmin(self.admin):
                    result = self.conn.select('domain', what='COUNT(domain) AS total',)
                else:
                    result = self.conn.query(
                        """
                        SELECT COUNT(domain.domain) AS total
                        FROM domain
                        LEFT JOIN domain_admins ON (domain.domain=domain_admins.domain)
                        WHERE domain_admins.username=%s
                        """ % (web.sqlquote(self.admin))
                    )

                total = result[0].total or 0
                return total
            except Exception, e:
                pass
        elif accountType == 'user':
            try:
                if self.isGlobalAdmin(self.admin):
                    result = self.conn.select('mailbox', what='COUNT(username) AS total')
                else:
                    self.sql_append_where = ''
                    if len(self.domains) == 0:
                        self.sql_append_where = 'AND mailbox.domain IN %s' % web.sqlquote(self.domains)

                    result = self.conn.query(
                        """
                        SELECT COUNT(mailbox.username) AS total
                        FROM mailbox
                        LEFT JOIN domain_admins ON (mailbox.domain = domain_admins.domain)
                        WHERE domain_admins.username = %s %s
                        """ % (web.sqlquote(self.admin), self.sql_append_where,)
                    )

                total = result[0].total or 0
                return total
            except:
                pass
        elif accountType == 'alias':
            try:
                if self.isGlobalAdmin(self.admin):
                    if len(self.domains) == 0:
                        result = self.conn.select(
                            'alias',
                            what='COUNT(address) AS total',
                            where='address <> goto',
                        )
                    else:
                        result = self.conn.select(
                            'alias',
                            what='COUNT(address) AS total',
                            where='address <> goto AND domain IN %s' % web.sqlquote(self.domains),
                        )
                else:
                    self.sql_append_where = ''
                    if len(self.domains) == 0:
                        self.sql_append_where = 'AND alias.domain IN %s' % web.sqlquote(self.domains)

                    result = self.conn.query(
                        """
                        SELECT COUNT(alias.address) AS total
                        FROM alias
                        LEFT JOIN domain_admins ON (alias.domain = domain_admins.domain)
                        WHERE domain_admins.username = %s AND alias.address <> alias.goto %s
                        """ % (web.sqlquote(self.admin), self.sql_append_where,)
                    )

                total = result[0].total or 0
                return total
            except:
                pass

        return 0

    @decorators.require_global_admin
    def delete(self, mails=[]):
        if not isinstance(mails, types.ListType):
            return (False, 'INVALID_MAIL')

        self.mails = [str(v).lower() for v in mails if iredutils.isEmail(v)]
        self.sqlMails = web.sqlquote(self.mails)

        # Delete domain and related records.
        try:
            self.conn.delete('admin', where='username IN %s' % self.sqlMails)
            self.conn.delete('domain_admins', where='username IN %s' % self.sqlMails)

            web.logger(msg="Delete admin: %s." % ', '.join(self.mails), event='delete',)
            return (True,)
        except Exception, e:
            return (False, str(e))

    @decorators.require_global_admin
    def enableOrDisableAccount(self, accounts, active=True):
        return self.setAccountStatus(accounts=accounts, active=active, accountType='admin',)

    def profile(self, mail):
        self.mail = web.safestr(mail)
        self.domainGlobalAdmin = False

        if not iredutils.isEmail(self.mail):
            return (False, 'INVALID_MAIL')

        self.sqladmin = web.sqlquote(self.mail)
        try:
            result = self.conn.select('admin', where='username=%s' % self.sqladmin, limit=1,)
            if len(result) == 1:
                if self.isGlobalAdmin(admin=self.mail):
                    self.domainGlobalAdmin = True

                return (True, self.domainGlobalAdmin, list(result)[0])
            else:
                return (False, 'INVALID_MAIL')
        except Exception, e:
            return (False, str(e))

    @decorators.require_global_admin
    def add(self, data):
        self.cn = data.get('cn', '')
        self.mail = web.safestr(data.get('mail')).strip().lower()

        if not iredutils.isEmail(self.mail):
            return (False, 'INVALID_MAIL')

        # Check admin exist.
        connutils = connUtils.Utils()
        if connutils.isAdminExists(self.mail):
            return (False, 'ALREADY_EXISTS')

        # Get domainGlobalAdmin setting.
        self.domainGlobalAdmin = 'yes'

        # Get language setting.
        self.preferredLanguage = web.safestr(data.get('preferredLanguage', 'en_US'))

        # Get new password.
        self.newpw = web.safestr(data.get('newpw'))
        self.confirmpw = web.safestr(data.get('confirmpw'))

        result = iredutils.verifyNewPasswords(self.newpw, self.confirmpw)

        if result[0] is True:
            self.passwd = result[1]
        else:
            return result

        try:
            self.conn.insert(
                'admin',
                username=self.mail,
                name=self.cn,
                password=iredutils.getSQLPassword(self.passwd),
                language=self.preferredLanguage,
                created=iredutils.sqlNOW,
                active='1',
            )

            if self.domainGlobalAdmin == 'yes':
                self.conn.insert(
                    'domain_admins',
                    username=self.mail,
                    domain='ALL',
                    created=iredutils.sqlNOW,
                    active='1',
                )

            web.logger(msg="Create admin: %s." % (self.mail), event='create',)
            return (True,)
        except Exception, e:
            return (False, str(e))

    @decorators.require_login
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = web.safestr(mail)

        if session.get('domainGlobalAdmin') is not True and session.get('username') != self.mail:
            # Don't allow to view/update other admins' profile.
            return (False, 'PERMISSION_DENIED')

        if self.profile_type == 'general':
            # Get name
            self.cn = data.get('cn', '')

            # Get preferred language.
            self.preferredLanguage = str(data.get('preferredLanguage', 'en_US'))

            # Update in SQL db.
            try:
                self.conn.update(
                    'admin',
                    where='username=%s' % web.sqlquote(self.mail),
                    name=self.cn,
                    language=self.preferredLanguage,
                )

                # Update language immediately.
                if session.get('username') == self.mail:
                    session['lang'] = self.preferredLanguage
            except Exception, e:
                return (False, str(e))

            if session.get('domainGlobalAdmin') is True:
                # Update account status
                self.accountStatus = '0'    # Disabled
                if 'accountStatus' in data.keys():
                    self.accountStatus = '1'    # Active

                try:
                    self.conn.update(
                        'admin',
                        where='username=%s' % web.sqlquote(self.mail),
                        active=self.accountStatus,
                    )
                except Exception, e:
                    return (False, str(e))

                # Update global admin.
                self.domainGlobalAdmin = True

                if self.domainGlobalAdmin is True:
                    try:
                        self.conn.delete(
                            'domain_admins',
                            where='username=%s' % web.sqlquote(self.mail),
                        )

                        self.conn.insert(
                            'domain_admins',
                            username=self.mail,
                            created=iredutils.sqlNOW,
                            domain='ALL',
                            active=self.accountStatus,
                        )
                    except Exception, e:
                        return (False, str(e))
                else:
                    try:
                        self.conn.delete(
                            'domain_admins',
                            where='username=%s AND domain="ALL"' % web.sqlquote(self.mail),
                        )
                    except Exception, e:
                        return (False, str(e))

                # Update managed domains.
                # Get domains from web form.
                self.newmds = [str(v).lower() for v in data.get('domainName', []) if iredutils.isDomain(v)]
                if len(self.newmds) > 0:
                    try:
                        # Delete all managed domains.
                        self.conn.delete(
                            'domain_admins',
                            where='username=%s AND domain <> "ALL"' % web.sqlquote(self.mail),
                        )

                        # Insert new domains.
                        v = []
                        for d in self.newmds:
                            v += [{'username': self.mail,
                                  'domain': d,
                                  'created': iredutils.sqlNOW,
                                  'active': self.accountStatus,
                                 }]
                        self.conn.multiple_insert(
                            'domain_admins',
                            values=v,
                        )
                    except Exception, e:
                        return (False, str(e))

        elif self.profile_type == 'password':
            self.cur_passwd = str(data.get('oldpw', ''))
            self.newpw = str(data.get('newpw', ''))
            self.confirmpw = str(data.get('confirmpw', ''))

            # Verify new passwords.
            qr = iredutils.verifyNewPasswords(self.newpw, self.confirmpw)
            if qr[0] is True:
                self.passwd = iredutils.getSQLPassword(qr[1])
            else:
                return qr

            if session.get('domainGlobalAdmin') is not True:
                # Verify old password.
                auth = core.Auth()
                qr = auth.auth(username=self.mail, password=self.cur_passwd, verifyPassword=True,)
                if qr[0] is False:
                    return qr

            # Hash/Encrypt new password.
            try:
                self.conn.update(
                    'admin',
                    where='username=%s' % web.sqlquote(self.mail),
                    password=self.passwd,
                )
            except Exception, e:
                return web.seeother('/profile/admin/password/%s?msg=%s' % (self.mail, str(e)))

        return (True,)
