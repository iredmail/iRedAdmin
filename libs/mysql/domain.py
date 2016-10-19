# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils
from libs.mysql import core, decorators, connUtils

session = web.config.get('_session')


class Domain(core.MySQLWrap):
    def __del__(self):
        pass

    @decorators.require_global_admin
    def enableOrDisableAccount(self, accounts, active=True):
        return self.setAccountStatus(accounts=accounts, active=active, accountType='domain',)

    def getAllDomains(self, columns=[],):
        """Get all domains. Return (True, [records])."""
        try:
            if columns:
                result = self.conn.select('domain', what=','.join(columns),)
            else:
                result = self.conn.select('domain')

            return (True, list(result))
        except Exception, e:
            return (False, str(e))

    def getDomainAdmins(self, domain, mailOnly=False):
        domain = str(domain)

        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        try:
            qr = self.conn.query(
                '''
                SELECT
                    admin.username, admin.name, admin.language, admin.active
                FROM admin
                LEFT JOIN domain_admins ON (domain_admins.username=admin.username)
                WHERE domain_admins.domain=$domain
                ''',
                vars={'domain': domain, },
            )

            if mailOnly is True:
                admins = []
                for adm in qr:
                    admins += [adm.username]
                return (True, admins)
            else:
                return (True, list(qr))
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def getCountsOfExistAccountsUnderDomain(self, domain, accountType='user'):
        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        sql_vars = {'domain': domain, }

        if accountType == 'user':
            try:
                qr1 = self.conn.select(
                    'mailbox',
                    vars=sql_vars,
                    what='COUNT(username) AS mailbox_count',
                    where='domain=$domain',
                )
                mailbox_count = qr1[0].mailbox_count or 0

                qr2 = self.conn.select(
                    'mailbox',
                    vars=sql_vars,
                    what='SUM(quota) AS quota_count',
                    where='domain=$domain',
                )
                quota_count = qr2[0].quota_count or 0
                return (True, mailbox_count, quota_count)
            except Exception, e:
                return (False, str(e))
        elif accountType == 'alias':
            try:
                result = self.conn.select(
                    'alias',
                    vars=sql_vars,
                    what='COUNT(address) AS alias_count',
                    where='domain = $domain AND address <> goto',
                )
                result = list(result)
                return (True, result[0].alias_count)
            except Exception, e:
                return (False, str(e))
        else:
            return (False, 'INVALID_ACCOUNT_TYPE')

    @decorators.require_domain_access
    def getAllocatedQuotaSize(self, domain):
        try:
            result = self.conn.select(
                'mailbox',
                vars={'domain': domain, },
                what='SUM(quota) AS total',
                where='domain = $domain',
            )
            result = list(result)
            return (True, result[0].total or 0)
        except Exception, e:
            return (False, str(e))

    # List all domains under control.
    def listAccounts(self, cur_page=1):
        admin = session.get('username')

        page = int(cur_page) or 1

        sql_where = ''
        if session.get('domainGlobalAdmin') is not True:
            sql_where = ' WHERE domain_admins.username = %s' % web.sqlquote(admin)

        # RAW sql command used to get records.
        rawSQLOfRecords = """
            SELECT
                a.domain, a.description, a.aliases, a.mailboxes, a.maxquota, a.quota,
                a.transport, a.backupmx, a.active,
                IFNULL(b.alias_count, 0) AS alias_count,
                IFNULL(c.mailbox_count, 0) AS mailbox_count,
                IFNULL(c.quota_count, 0) AS quota_count
            FROM domain AS a
            LEFT JOIN (
                SELECT domain, COUNT(address) AS alias_count
                FROM alias
                WHERE
                    address<>goto
                    AND address<>domain
                    AND address NOT IN (SELECT username FROM mailbox)
                GROUP BY domain
                ) AS b ON (a.domain=b.domain)
            LEFT JOIN (
                SELECT domain,
                    SUM(mailbox.quota) AS quota_count,
                    COUNT(username) AS mailbox_count
                FROM mailbox
                GROUP BY domain
                ) AS c ON (a.domain=c.domain)
            LEFT JOIN domain_admins ON (domain_admins.domain=a.domain)
            %s
            GROUP BY a.domain
            ORDER BY a.domain
            LIMIT %d
            OFFSET %d
        """ % (sql_where, settings.PAGE_SIZE_LIMIT, (page - 1) * settings.PAGE_SIZE_LIMIT,)

        if self.is_global_admin(admin):
            try:
                resultOfTotal = self.conn.select(
                    'domain',
                    what='COUNT(domain) AS total',
                )

                resultOfRecords = self.conn.query(rawSQLOfRecords)
            except Exception, e:
                return (False, str(e))
        else:
            try:
                resultOfTotal = self.conn.select(
                    ['domain', 'domain_admins', ],
                    vars={'admin': admin, },
                    what='COUNT(domain.domain) AS total',
                    where='domain.domain = domain_admins.domain AND domain_admins.username = $admin',
                )

                resultOfRecords = self.conn.query(rawSQLOfRecords)
            except Exception, e:
                return (False, str(e))

        if len(resultOfTotal) == 1:
            total = resultOfTotal[0].total or 0
        else:
            total = 0

        return (True, total, list(resultOfRecords),)

    @decorators.require_global_admin
    def delete(self, domains=None, keep_mailbox_days=0):
        if not domains:
            return (False, 'INVALID_DOMAIN_NAME')

        domains = [str(v).lower() for v in domains if iredutils.is_domain(v)]

        if not domains:
            return (True, )

        if keep_mailbox_days == 0:
            keep_mailbox_days = 36500

        sql_vars = {'domains': domains,
                    'admin': session.get('username'),
                    'keep_mailbox_days': keep_mailbox_days}

        # Log maildir paths of existing users
        try:
            sql_raw = '''
                INSERT INTO deleted_mailboxes (username, maildir, domain, admin, delete_date)
                SELECT username, \
                       CONCAT(storagebasedirectory, '/', storagenode, '/', maildir) AS maildir, \
                       domain, \
                       $admin, \
                       DATE_ADD(NOW(), INTERVAL $keep_mailbox_days DAY)
                  FROM mailbox
                 WHERE domain IN $domains'''

            self.conn.query(sql_raw, vars=sql_vars)
        except Exception, e:
            print e
            pass

        # Delete domain and related records.
        try:
            self.conn.delete('domain', vars=sql_vars, where='domain IN $domains', )

            self.conn.delete(
                'alias_domain',
                vars=sql_vars,
                where='alias_domain IN $domains OR target_domain IN $domains',
            )

            for tbl in ['alias', 'domain_admins', 'mailbox',
                        'recipient_bcc_domain', 'recipient_bcc_user',
                        'sender_bcc_domain', 'sender_bcc_user']:
                self.conn.delete(tbl,
                                 vars=sql_vars,
                                 where='domain IN $domains')

            # Delete real-time mailbox quota.
            try:
                self.conn.query('DELETE FROM %s WHERE %s' % (settings.SQL_TBL_USED_QUOTA,
                                                             web.sqlors('username LIKE ', ['%@' + d for d in domains])))
            except:
                pass

            for d in domains:
                web.logger(msg="Delete domain: %s." % (d), domain=d, event='delete',)

            return (True,)
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def simpleProfile(self, domain, columns=[]):
        domain = web.safestr(domain)

        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        try:
            qr = self.conn.select('domain',
                                  vars={'domain': domain, },
                                  what=','.join(columns) or '*',
                                  where='domain=$domain')

            if len(qr) == 1:
                # Return first list element.
                return (True, list(qr)[0])
            else:
                return (False, 'NO_SUCH_OBJECT')
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def profile(self, domain):
        domain = web.safestr(domain)

        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        try:
            qr = self.conn.query(
                '''
                SELECT
                    domain.*,
                    sbcc.bcc_address AS sbcc_addr,
                    sbcc.active AS sbcc_active,
                    rbcc.bcc_address AS rbcc_addr,
                    rbcc.active AS rbcc_active,
                    alias.goto AS catchall,
                    alias.active AS catchall_active,
                    COUNT(DISTINCT mailbox.username) AS mailbox_count,
                    COUNT(DISTINCT alias.address) AS alias_count
                FROM domain
                LEFT JOIN sender_bcc_domain AS sbcc ON (sbcc.domain=domain.domain)
                LEFT JOIN recipient_bcc_domain AS rbcc ON (rbcc.domain=domain.domain)
                LEFT JOIN domain_admins ON (domain.domain = domain_admins.domain)
                LEFT JOIN mailbox ON (domain.domain = mailbox.domain)
                LEFT JOIN alias ON (
                    domain.domain = alias.address
                    AND alias.address <> alias.goto
                    )
                WHERE domain.domain=$domain
                GROUP BY
                    domain.domain, domain.description, domain.aliases,
                    domain.mailboxes, domain.maxquota, domain.quota,
                    domain.transport, domain.backupmx, domain.active
                ORDER BY domain.domain
                LIMIT 1
                ''',
                vars={'domain': domain, },
            )

            if len(qr) == 1:
                # Return first list element.
                return (True, list(qr)[0])
            else:
                return (False, 'NO_SUCH_OBJECT')
        except Exception, e:
            return (False, str(e))

    @decorators.require_global_admin
    def add(self, data):
        domain = web.safestr(data.get('domainName', '')).strip().lower()

        # Get company/organization name.
        cn = data.get('cn', '')

        # Check domain name.
        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        # Check whether domain name already exist (domainName, domainAliasName).
        connutils = connUtils.Utils()
        if connutils.is_domain_exists(domain):
            return (False, 'ALREADY_EXISTS')

        # Add domain in database.
        try:
            self.conn.insert(
                'domain',
                domain=domain,
                description=cn,
                transport=settings.default_mta_transport,
                created=iredutils.get_gmttime(),
                active='1',
            )
            web.logger(msg="Create domain: %s." % (domain), domain=domain, event='create',)
        except Exception, e:
            return (False, str(e))

        return (True,)

    @decorators.require_domain_access
    def update(self, domain, profile_type, data,):
        profile_type = str(profile_type)
        domain = str(domain)

        # Pre-defined update key:value.
        updates = {'modified': iredutils.get_gmttime(), }

        sql_vars = {'domain': domain, }

        if profile_type == 'general':
            # Get name
            cn = data.get('cn', '')
            updates['description'] = cn

            if session.get('domainGlobalAdmin') is True:
                # Get account status
                if 'accountStatus' in data.keys():
                    updates['active'] = 1
                else:
                    updates['active'] = 0

                # Update SQL db with columns: maxquota, active.
                try:
                    self.conn.update(
                        'domain',
                        vars=sql_vars,
                        where='domain=$domain',
                        **updates
                    )
                except Exception, e:
                    return (False, str(e))

        return (True,)
