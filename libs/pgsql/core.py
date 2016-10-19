# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils

session = web.config.get('_session')


class PGSQLWrap:
    def __init__(self):
        # Initial DB connection and cursor.
        try:
            self.conn = web.database(
                dbn='postgres',
                host=settings.vmail_db_host,
                port=int(settings.vmail_db_port),
                db=settings.vmail_db_name,
                user=settings.vmail_db_user,
                pw=settings.vmail_db_password,
            )
            self.conn.supports_multiple_insert = True
        except:
            return False

    # Validators.
    def is_global_admin(self, admin=None,):
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

    def is_domainAdmin(self, domain, admin=session.get('username'),):
        if not iredutils.is_domain(domain) or not iredutils.is_email(admin):
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
            accounts = [str(v) for v in accounts if iredutils.is_domain(v)]
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
            accounts = [str(v) for v in accounts if iredutils.is_email(v)]
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
            accounts = [str(v) for v in accounts if iredutils.is_email(v)]
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
            accounts = [str(v) for v in accounts if iredutils.is_email(v)]
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

    def deleteAccounts(self, accounts, accountType, keep_mailbox_days=0):
        # accounts must be a list/tuple.
        # accountType in ['domain', 'user', 'admin', 'alias',]
        if not accounts:
            return (True,)

        accountType = str(accountType)

        if accountType == 'domain':
            accounts = [str(v) for v in accounts if iredutils.is_domain(v)]
            try:
                self.conn.delete(
                    'domain',
                    vars={'accounts': accounts, },
                    where='domain IN $accounts',
                )
            except Exception, e:
                return (False, str(e))
        elif accountType == 'user':
            accounts = [str(v) for v in accounts if iredutils.is_email(v)]

            # Keep mailboxes 'forever', set to 100 years.
            if keep_mailbox_days == 0:
                keep_mailbox_days = 36500

            sql_vars = {'accounts': accounts,
                        'admin': session.get('username'),
                        'keep_mailbox_days': keep_mailbox_days}

            try:
                sql_raw = '''
                    INSERT INTO deleted_mailboxes (username, maildir, domain, admin, delete_date)
                    SELECT username, \
                           storagebasedirectory || '/' || storagenode || '/' || maildir, \
                           SPLIT_PART(username, '@', 2), \
                           $admin, \
                           CURRENT_TIMESTAMP + INTERVAL '$keep_mailbox_days DAYS'
                      FROM mailbox
                     WHERE username IN $accounts'''

                self.conn.query(sql_raw, vars=sql_vars)

                for tbl in ['mailbox', settings.SQL_TBL_USED_QUOTA,
                            'recipient_bcc_user', 'sender_bcc_user']:
                    self.conn.delete(tbl,
                                     vars=sql_vars,
                                     where='username IN $accounts')

                self.conn.delete('alias',
                                 vars=sql_vars,
                                 where='address IN $accounts')

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
                            modified=iredutils.get_gmttime(),
                        )
                except Exception, e:
                    pass

            except Exception, e:
                return (False, str(e))
        elif accountType == 'admin':
            accounts = [str(v) for v in accounts if iredutils.is_email(v)]
            try:
                self.conn.delete(
                    'admin',
                    vars={'accounts': accounts, },
                    where='username IN $accounts',
                )
            except Exception, e:
                return (False, str(e))
        elif accountType == 'alias':
            accounts = [str(v) for v in accounts if iredutils.is_email(v)]
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
        if not iredutils.is_email(username):
            return (False, 'INVALID_USERNAME')

        if len(password) == 0:
            return (False, 'EMPTY_PASSWORD')

        session['isMailUser'] = False
        # Query account from SQL database.
        if accountType == 'admin':
            # separate admin accounts
            result = self.conn.select(
                'admin',
                vars={'username': username, },
                where="username=$username AND active=1",
                limit=1,
            )

            # mail users as domain admin
            if not result:
                # Don't specify what= to work with old versions of iRedMail
                result = self.conn.select(
                    'mailbox',
                    vars={'username': username, },
                    where="username=$username AND active=1 AND isadmin=1",
                    limit=1,
                )
                if result:
                    session['isMailUser'] = True
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

        # Verify password
        authenticated = False
        if iredutils.verify_password_hash(password_sql, password):
            authenticated = True

        if authenticated is False:
            return (False, 'INVALID_CREDENTIALS')

        if verifyPassword is not True:
            session['username'] = username
            session['logged'] = True
            # Set preferred language.
            session['lang'] = web.safestr(record.get('language', 'en_US'))

            # Set session['domainGlobalAdmin']
            try:
                if session.get('isMailUser'):
                    if record.get('isglobaladmin', 0) == 1:
                        session['domainGlobalAdmin'] = True
                else:
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
            if 'mail' in kw.keys() and iredutils.is_email(kw.get('mail')):
                self.domain = web.safestr(kw['mail']).split('@')[-1]
            elif 'domain' in kw.keys() and iredutils.is_domain(kw.get('domain')):
                self.domain = web.safestr(kw['domain'])
            else:
                return False

            self.admin = session.get('username')
            if not iredutils.is_email(self.admin):
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
