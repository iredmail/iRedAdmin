# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils, settings
from libs.pgsql import core, decorators, connUtils

cfg = web.iredconfig
session = web.config.get('_session')


class Admin(core.PGSQLWrap):
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

    @decorators.require_global_admin
    def listAccounts(self, cur_page=1,):
        '''List all admins.'''
        # Pre-defined.
        total = 0

        # Get current page.
        cur_page = int(cur_page)

        self.sql_limit = ''
        if cur_page > 0:
            self.sql_limit = 'LIMIT %d OFFSET %d' % (
                settings.PAGE_SIZE_LIMIT,
                (cur_page - 1) * settings.PAGE_SIZE_LIMIT,
            )

        try:
            result = self.conn.select('admin', what='COUNT(username) AS total')
            if len(result) > 0:
                total = result[0].total or 0
        except Exception:
            pass

        try:
            result = self.conn.query(
                """
                SELECT name, username, language, created, active
                FROM admin
                ORDER BY username ASC
                %s
                """ % (self.sql_limit)
            )
            return (True, total, list(result))
        except Exception, e:
            return (False, str(e))

    # Get number of domains under control.
    def getNumberOfManagedAccounts(self, admin=None, accountType='domain', domains=[], ):
        if admin is None:
            self.admin = session.get('username')
        else:
            self.admin = str(admin)

        if not iredutils.isEmail(self.admin):
            return 0

        self.domains = []
        if accountType in ['user', 'alias', ]:
            if len(domains) > 0:
                self.domains = [str(d).lower() for d in domains if iredutils.isDomain(d)]
            else:
                connutils = connUtils.Utils()
                qr = connutils.getManagedDomains(admin=self.admin, domainNameOnly=True)
                if qr[0] is True:
                    self.domains = qr[1]

        sql_vars = {'admin': self.admin, 'domains': self.domains, }
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
                        WHERE domain_admins.username=$admin
                        """,
                        vars=sql_vars,
                    )

                total = result[0].total or 0
                return total
            except Exception:
                pass
        elif accountType == 'user':
            try:
                if self.isGlobalAdmin(self.admin):
                    if len(self.domains) >= 0:
                        result = self.conn.select(
                            'mailbox',
                            vars=sql_vars,
                            what='COUNT(username) AS total',
                            where='domain IN $domains',
                        )
                    else:
                        result = self.conn.select('mailbox', what='COUNT(username) AS total')
                else:
                    self.sql_append_where = ''
                    if len(self.domains) > 0:
                        self.sql_append_where = 'AND mailbox.domain IN %s' % web.sqlquote(self.domains)

                    result = self.conn.query(
                        """
                        SELECT COUNT(mailbox.username) AS total
                        FROM mailbox
                        LEFT JOIN domain_admins ON (mailbox.domain = domain_admins.domain)
                        WHERE domain_admins.username=$admin %s
                        """ % (self.sql_append_where, ),
                        vars=sql_vars,
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
                            vars=sql_vars,
                            what='COUNT(address) AS total',
                            where='address <> goto AND domain IN $domains',
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
                        WHERE domain_admins.username=$admin AND alias.address <> alias.goto %s
                        """ % (self.sql_append_where, ),
                        vars=sql_vars,
                    )

                total = result[0].total or 0
                return total
            except:
                pass

        return 0

    @decorators.require_global_admin
    def delete(self, mails=[]):
        if not isinstance(mails, list):
            return (False, 'INVALID_MAIL')

        self.mails = [str(v).lower() for v in mails if iredutils.isEmail(v)]
        sql_vars = {'username': self.mails, }

        # Delete domain and related records.
        try:
            self.conn.delete(
                'admin',
                vars=sql_vars,
                where='username IN $username',
            )
            self.conn.delete(
                'domain_admins',
                vars=sql_vars,
                where='username IN $username',
            )

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

        try:
            result = self.conn.select(
                'admin',
                vars={'username': self.mail, },
                where='username=$username',
                limit=1,
            )
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
        self.domainGlobalAdmin = web.safestr(data.get('domainGlobalAdmin', 'no'))
        if self.domainGlobalAdmin not in ['yes', 'no', ]:
            self.domainGlobalAdmin = 'no'

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
                created=iredutils.getGMTTime(),
                active='1',
            )

            if self.domainGlobalAdmin == 'yes':
                self.conn.insert(
                    'domain_admins',
                    username=self.mail,
                    domain='ALL',
                    created=iredutils.getGMTTime(),
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

        sql_vars = {'username': self.mail, }

        if self.profile_type == 'general':
            # Get name
            self.cn = data.get('cn', '')

            # Get preferred language.
            self.preferredLanguage = str(data.get('preferredLanguage', 'en_US'))

            # Update in SQL db.
            try:
                self.conn.update(
                    'admin',
                    vars=sql_vars,
                    where='username=$username',
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
                        vars=sql_vars,
                        where='username=$username',
                        active=self.accountStatus,
                    )
                except Exception, e:
                    return (False, str(e))

        elif self.profile_type == 'password':
            self.cur_passwd = str(data.get('oldpw', ''))
            self.newpw = web.safestr(data.get('newpw', ''))
            self.confirmpw = web.safestr(data.get('confirmpw', ''))

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
                    vars=sql_vars,
                    where='username=$username',
                    password=self.passwd,
                    passwordlastchange=iredutils.getGMTTime(),
                )
            except Exception, e:
                raise web.seeother('/profile/admin/password/%s?msg=%s' % (self.mail, web.urlquote(e)))

        return (True,)
