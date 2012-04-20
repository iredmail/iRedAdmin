# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils, md5crypt

cfg = web.iredconfig
session = web.config.get('_session')


class PGSQLWrap:
    def __init__(self, app=web.app, session=session, **settings):
        # Initial DB connection and cursor.
        try:
            self.conn = web.database(
                dbn='postgres',
                host=cfg.vmaildb.get('host', '127.0.0.1'),
                port=int(cfg.vmaildb.get('port', 5432)),
                db=cfg.vmaildb.get('db', 'vmail'),
                user=cfg.vmaildb.get('user', 'vmailadmin'),
                pw=cfg.vmaildb.get('passwd', ''),
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
                vars={'username': admin, 'domain': 'ALL', },
                what='username',
                where='username=$username AND domain=$domain',
                limit=1,
            )
            if len(result) == 1:
                return True
            else:
                return False
        except Exception:
            return False

    def isDomainAdmin(self, domain, admin=session.get('username'),):
        if not iredutils.isDomain(domain) or not iredutils.isEmail(admin):
            return False

        if admin == session.get('username') \
           and session.get('domainGlobalAdmin') is True:
            return True

        try:
            result = self.conn.select(
                'domain_admins',
                vars={'domain': domain, 'username': admin, },
                what='username',
                where='domain=$domain AND username=$username AND active=1',
                limit=1,
            )
            if len(result) == 1:
                return True
            else:
                return False
        except Exception:
            return False

    def setAccountStatus(self, accounts, accountType, active=True):
        # accounts must be a list/tuple.
        # accountType in ['domain', 'user', 'admin', 'alias',]
        # active: True -> active, False -> disabled
        if not len(accounts) > 0:
            return (True,)

        accountType = str(accountType)
        if active is True:
            active = 1
            action = 'Active'
        else:
            active = 0
            action = 'Disable'

        if accountType == 'domain':
            accounts = [str(v) for v in accounts if iredutils.isDomain(v)]
            try:
                self.conn.update(
                    'domain',
                    vars={'accounts': accounts},
                    where='domain IN $accounts',
                    active=active,
                )
            except Exception, e:
                return (False, str(e))
        elif accountType == 'user':
            accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.update(
                    'mailbox',
                    vars={'accounts': accounts},
                    where='username IN $accounts',
                    active=active,
                )
            except Exception, e:
                return (False, str(e))
        elif accountType == 'admin':
            accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.update(
                    'admin',
                    vars={'accounts': accounts},
                    where='username IN $accounts',
                    active=active,
                )
            except Exception, e:
                return (False, str(e))
        elif accountType == 'alias':
            accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.update(
                    'alias',
                    vars={'accounts': accounts},
                    where='address IN $accounts',
                    active=active,
                )
            except Exception, e:
                return (False, str(e))
        else:
            pass

        try:
            web.logger(
                msg="%s %s: %s." % (action, accountType, ', '.join(accounts)),
                event=action.lower(),
            )
        except:
            pass
        return (True,)

    def deleteAccounts(self, accounts, accountType,):
        # accounts must be a list/tuple.
        # accountType in ['domain', 'user', 'admin', 'alias',]
        if not accounts:
            return (True,)

        accountType = str(accountType)

        if accountType == 'domain':
            accounts = [str(v) for v in accounts if iredutils.isDomain(v)]
            try:
                self.conn.delete(
                    'domain',
                    vars={'accounts': accounts, },
                    where='domain IN $accounts',
                )
            except Exception, e:
                return (False, str(e))
        elif accountType == 'user':
            accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            sql_vars = {'accounts': accounts, }
            try:
                self.conn.delete(
                    'mailbox',
                    vars=sql_vars,
                    where='username IN $accounts',
                )
                self.conn.delete(
                    'alias',
                    vars=sql_vars,
                    where='address IN $accounts',
                )
                self.conn.delete(
                    'recipient_bcc_user',
                    vars=sql_vars,
                    where='username IN $accounts',
                )
                self.conn.delete(
                    'sender_bcc_user',
                    vars=sql_vars,
                    where='username IN $accounts',
                )

                # Remove users from alias.goto.
                try:
                    qr = self.conn.select(
                        'alias',
                        what='address,goto',
                        where='address <> goto AND address <> "" AND (%s)' % ' OR '.join(
                            ['goto LIKE %s' % web.sqlquote('%%' + v + '%%') for v in accounts]
                        ),
                    )

                    # Update aliases, remove deleted users.
                    for als in qr:
                        exist_members = [v for v in str(als.goto).replace(' ', '').split(',')]

                        # Skip if PGSQL pattern matching doesn't get correct results.
                        if not set(accounts) & set(exist_members):
                            continue

                        self.conn.update(
                            'alias',
                            vars={'address': als.address, },
                            where='address = $address',
                            goto=','.join([str(v) for v in exist_members if v not in accounts]),
                            modified=iredutils.getGMTTime(),
                        )
                except Exception, e:
                    pass

            except Exception, e:
                return (False, str(e))
        elif accountType == 'admin':
            accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.delete(
                    'admin',
                    vars={'accounts': accounts, },
                    where='username IN $accounts',
                )
            except Exception, e:
                return (False, str(e))
        elif accountType == 'alias':
            accounts = [str(v) for v in accounts if iredutils.isEmail(v)]
            try:
                self.conn.delete(
                    'alias',
                    vars={'accounts': accounts, },
                    where='address IN $accounts',
                )
            except Exception, e:
                return (False, str(e))
        else:
            pass

        try:
            web.logger(
                msg="Delete %s: %s." % (accountType, ', '.join(accounts)),
                event='delete',
            )
        except:
            pass
        return (True,)


class Auth(PGSQLWrap):
    def auth(self, username, password, accountType='admin', verifyPassword=False,):
        if not iredutils.isEmail(username):
            return (False, 'INVALID_USERNAME')

        if len(password) == 0:
            return (False, 'EMPTY_PASSWORD')

        # Query account from SQL database.
        if accountType == 'admin':
            result = self.conn.select(
                'admin',
                vars={'username': username, },
                where="username=$username AND active=1",
                limit=1,
            )
        elif accountType == 'user':
            result = self.conn.select(
                'mailbox',
                vars={'username': username, },
                where="username=$username AND active=1",
                limit=1,
            )
        else:
            return (False, 'INVALID_ACCOUNT_TYPE')

        if len(result) != 1:
            # Account not found.
            # Do NOT return msg like 'Account does not ***EXIST***', crackers
            # can use it to verify valid accounts.
            return (False, 'INVALID_CREDENTIALS')

        # It's a valid account.
        record = result[0]
        password_sql = str(record.password)

        # Verify password.
        authenticated = False
        if password_sql.startswith('$') and len(password_sql) == 34 and password_sql.count('$') == 3:
            # Password is considered as a MD5 password (with salt).
            # Get salt string from password which stored in SQL.
            tmpsalt = password_sql.split('$')
            tmpsalt[-1] = ''
            salt = '$'.join(tmpsalt)

            if md5crypt.md5crypt(password, salt) == password_sql:
                authenticated = True

        elif password_sql == iredutils.getPlainMD5Password(password):
            # Plain MD5
            authenticated = True
        elif password_sql.upper().startswith('{PLAIN-MD5}'):
            if password_sql == '{PLAIN-MD5}' + iredutils.getPlainMD5Password(password):
                authenticated = True
        elif password_sql.upper().startswith('{PLAIN}'):
            # Plain password with prefix '{PLAIN}'.
            if password_sql == '{PLAIN}' + password:
                authenticated = True
        elif password_sql == password:
            # Plain password.
            authenticated = True

        # Compare passwords.
        if authenticated is False:
            return (False, 'INVALID_CREDENTIALS')

        if verifyPassword is not True:
            session['username'] = username
            session['logged'] = True
            # Set preferred language.
            session['lang'] = str(record.language) or 'en_US'

            # Set session['domainGlobalAdmin']
            try:
                result = self.conn.select(
                    'domain_admins',
                    vars={'username': username, 'domain': 'ALL', },
                    what='domain',
                    where='username=$username AND domain=$domain',
                    limit=1,
                )
                if len(result) == 1:
                    session['domainGlobalAdmin'] = True
            except:
                pass

        return (True,)


class PGSQLDecorators(PGSQLWrap):
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
                        vars={'username': self.admin, 'domain': [self.domain, 'ALL']},
                        what='username',
                        where='username=$username AND domain IN $domain',
                    )
                except Exception:
                    result = {}

                if len(result) != 1:
                    return func(self, *args, **kw)
                else:
                    raise web.seeother('/users' + '?msg=PERMISSION_DENIED&domain=' + self.domain)
        return proxyfunc
