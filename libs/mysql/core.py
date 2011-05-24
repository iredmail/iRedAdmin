# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils, md5crypt

cfg = web.iredconfig
session = web.config.get('_session')

class MySQLWrap:
    def __init__(self, app=web.app, session=session, **settings):
        # Create DB connection and cursor.
        try:
            self.conn = web.database(
                dbn='mysql',
                host=str(cfg.vmaildb.get('host', '127.0.0.1')),
                port=int(cfg.vmaildb.get('port', 3306)),
                user=str(cfg.vmaildb.get('user', 'vmailadmin')),
                pw=str(cfg.vmaildb.get('passwd', '')),
                db=str(cfg.vmaildb.get('db', 'vmail')),
            )
            self.conn.supports_multiple_insert = True
        except:
            return False

    # Validators.
    def isGlobalAdmin(self, admin=None,):
        if admin is None:
            return False
        elif admin == session.get('username'):
            if session.get('domainGlobalAdmin') is True:
                return True
            else:
                return False

        admin = str(admin)

        # Not logged admin.
        try:
            result = self.conn.select(
                'domain_admins',
                what='username',
                where='''username=%s AND domain="ALL"''' % web.sqlquote(admin),
                limit=1,
            )
            if len(result) == 1:
                return True
            else:
                return False
        except Exception, e:
            return False

    def isDomainAdmin(self, domain, admin=session.get('username'),):
        if not iredutils.isDomain(domain) or not iredutils.isEmail(admin):
            return False

        if admin == session.get('username') and session.get('domainGlobalAdmin') is True:
            return True

        try:
            result = self.conn.select(
                'domain_admins',
                what='username',
                where='domain=%s AND username=%s AND active=1' % (
                    web.sqlquote(domain),
                    web.sqlquote(admin),
                ),
                limit=1,
            )
            if len(result) == 1:
                return True
            else:
                return False
        except Exception, e:
            return False

    def setAccountStatus(self, accounts, accountType, active=True):
        # accounts must be a list/tuple.
        # accountType in ['domain', 'user', 'admin', 'alias',]
        # active: True -> active, False -> disabled
        if not len(accounts) > 0:
            return (True,)

        self.accountType = str(accountType)
        if active is True:
            self.active = 1
            self.action = 'Active'
        else:
            self.active = 0
            self.action = 'Disable'

        if self.accountType == 'domain':
            self.accounts = [str(v) for v in accounts if iredutils.isDomain(v)]
            try:
                self.conn.update(
                    'domain',
                    where='domain IN %s' % (web.sqlquote(self.accounts)),
                    active=self.active,
                )
            except Exception, e:
                return (False, str(e))
        elif self.accountType == 'user':
            self.accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.update(
                    'mailbox',
                    where='username IN %s' % (web.sqlquote(self.accounts)),
                    active=self.active,
                )
            except Exception, e:
                return (False, str(e))
        elif self.accountType == 'admin':
            self.accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.update(
                    'admin',
                    where='username IN %s' % (web.sqlquote(self.accounts)),
                    active=self.active,
                )
            except Exception, e:
                return (False, str(e))
        elif self.accountType == 'alias':
            self.accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.update(
                    'alias',
                    where='address IN %s' % (web.sqlquote(self.accounts)),
                    active=self.active,
                )
            except Exception, e:
                return (False, str(e))
        else:
            pass

        try:
            web.logger(
                msg="%s %s: %s." % (self.action, self.accountType, ', '.join(self.accounts)),
                event=self.action.lower(),
            )
        except:
            pass
        return (True,)

    def getUsedBytesMessages(self, domain=None):
        """Return (messages, bytes)"""
        if domain is None:
            resultOfSum = self.conn.query(
                '''
                SELECT
                    SUM(messages) AS messages,
                    SUM(bytes) AS bytes
                FROM mailbox
                '''
            )
            counterOfSum = resultOfSum[0]
        else:
            if not iredutils.isDomain(domain):
                return (0, 0)

            # Check domain access
            if self.isDomainAdmin(domain=domain, admin=session.get('username'),):
                resultOfSum = self.conn.query(
                    '''
                    SELECT
                        SUM(messages) AS messages,
                        SUM(bytes) AS bytes
                    FROM mailbox
                    WHERE domain = %s
                    ''' % web.sqlquote(domain)
                )
                counterOfSum = resultOfSum[0]
            else:
                return (0, 0)

        return (counterOfSum.messages, counterOfSum.bytes)


class Auth(MySQLWrap):
    def auth(self, username, password, verifyPassword=False,):
        if not iredutils.isEmail(username):
            return (False, 'INVALID_USERNAME')

        if len(password) == 0:
            return (False, 'EMPTY_PASSWORD')

        # Query admin.
        result = self.conn.select(
            'admin',
            where="username=%s AND active=1" % web.sqlquote(username),
            limit=1,
        )

        if len(result) == 1:
            # It's a valid admin.
            record = result[0]

            # Get salt string from password which stored in SQL.
            tmpsalt = str(record.password).split('$')
            tmpsalt[-1] = ''
            salt = '$'.join(tmpsalt)

            # Compare passwords.
            if md5crypt.md5crypt(password, salt) == str(record.password):
                if verifyPassword is not True:
                    session['username'] = username
                    session['logged'] = True
                    # Set preferred language.
                    session['lang'] = str(record.language) or 'en_US'

                    # Set session['domainGlobalAdmin']
                    try:
                        result = self.conn.select(
                            'domain_admins',
                            what='domain',
                            where='''username=%s AND domain="ALL"''' % web.sqlquote(username),
                            limit=1,
                        )
                        if len(result) == 1:
                            session['domainGlobalAdmin'] = True
                    except:
                        pass

                return (True,)
            else:
                return (False, 'INVALID_CREDENTIALS')
        else:
            return (False, 'INVALID_CREDENTIALS')


class MySQLDecorators(MySQLWrap):
    def __del__(self):
        pass

    def require_global_admin(self, func):
        def proxyfunc(self, *args, **kw):
            if session.get('domainGlobalAdmin') is True:
                return func(self, *args, **kw)
            else:
                return False
        return proxyfunc

    def require_domain_access(self, func):
        def proxyfunc(self, *args, **kw):
            if 'mail' in kw.keys() and iredutils.isEmail(kw.get('mail')):
                self.domain = web.safestr(kw['mail']).split('@')[-1]
            elif 'domain' in kw.keys() and iredutils.isDomain(kw.get('domain')):
                self.domain = web.safestr(kw['domain'])
            else:
                return False

            self.admin = session.get('username')
            if not iredutils.isEmail(self.admin):
                return False

            # Check domain global admin.
            if session.get('domainGlobalAdmin') is True:
                return func(self, *args, **kw)
            else:
                # Check whether is domain admin.
                try:
                    result = self.conn.select(
                        'domain_admins',
                        what='username',
                        where='''username=%s AND domain IN %s''' % (
                            web.sqlquote(self.admin),
                            web.sqlquote([self.domain, 'ALL']),
                        ),
                    )
                except Exception, e:
                    result = {}

                if len(result) != 1:
                    return func(self, *args, **kw)
                else:
                    return web.seeother('/users' + '?msg=PERMISSION_DENIED&domain=' + self.domain)
        return proxyfunc
