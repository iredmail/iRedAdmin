# Author: Zhang Huangbin <zhb@iredmail.org>

import types
import web
from libs import iredutils
from libs.mysql import core, decorators, connUtils

cfg = web.iredconfig
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
        self.domain = str(domain)

        if not iredutils.isDomain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        try:
            qr = self.conn.query(
                '''
                SELECT
                    admin.username, admin.name, admin.language,
                    admin.created, admin.active
                FROM admin
                LEFT JOIN domain_admins ON (domain_admins.username=admin.username)
                WHERE domain_admins.domain=%s
                ''' % web.sqlquote(self.domain)
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

    def getAllAliasDomains(self, domain):
        self.domain = str(domain)

        if not iredutils.isDomain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        try:
            qr = self.conn.select('alias_domain', where='target_domain=%s' % web.sqlquote(self.domain))
            return (True, list(qr))
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def getCountsOfExistAccountsUnderDomain(self, domain, accountType='user'):
        if not iredutils.isDomain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        self.sql_domain = web.sqlquote(domain)
        if accountType == 'user':
            try:
                qr1 = self.conn.select(
                    'mailbox',
                    what='COUNT(username) AS mailbox_count',
                    where='domain = %s' % self.sql_domain,
                )
                mailbox_count = qr1[0].mailbox_count or 0

                qr2 = self.conn.select(
                    'mailbox',
                    what='SUM(quota) AS quota_count',
                    where='domain = %s' % self.sql_domain,
                )
                quota_count = qr2[0].quota_count or 0
                return (True, mailbox_count, quota_count)
            except Exception, e:
                return (False, str(e))
        elif accountType == 'alias':
            try:
                result = self.conn.select(
                    'alias',
                    what='COUNT(address) AS alias_count',
                    where='domain = %s AND address <> goto' % self.sql_domain,
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
                what='SUM(quota) AS total',
                where='domain = %s' % web.sqlquote(domain),
            )
            result = list(result)
            return (True, result[0].total or 0)
        except Exception, e:
            return (False, str(e))

    # List all domains under control.
    def listAccounts(self, cur_page=1):
        self.admin = session.get('username')

        try:
            self.cur_page = int(cur_page)
        except:
            self.cur_page = 1

        self.sql_where = ''
        if session.get('domainGlobalAdmin') is not True:
            self.sql_where = ' WHERE domain_admins.username = %s' % web.sqlquote(self.admin)

        # RAW sql command used to get records.
        self.rawSQLOfRecords = """
            SELECT
                a.domain, a.description, a.aliases, a.mailboxes, a.maxquota, a.quota,
                a.transport, a.backupmx, a.created, a.active,
                IFNULL(b.alias_count,0) AS alias_count,
                IFNULL(c.mailbox_count,0) AS mailbox_count,
                IFNULL(c.stored_quota,0) AS stored_quota,
                IFNULL(c.quota_count,0) AS quota_count
            FROM domain AS a
            LEFT JOIN (SELECT domain, COUNT(*) AS alias_count FROM alias GROUP BY domain) AS b ON (a.domain=b.domain)
            LEFT JOIN (SELECT domain, SUM(mailbox.bytes) AS stored_quota, SUM(mailbox.quota) AS quota_count, COUNT(*) AS mailbox_count FROM mailbox GROUP BY domain) AS c ON (a.domain=c.domain)
            LEFT JOIN domain_admins ON (domain_admins.domain=a.domain)
            %s
            GROUP BY a.domain
            ORDER BY a.domain
            LIMIT %d
            OFFSET %d
        """ % (self.sql_where, session['pageSizeLimit'],
               (self.cur_page-1)*session['pageSizeLimit'],
              )

        if self.isGlobalAdmin(self.admin):
            try:
                resultOfTotal = self.conn.select(
                    ['domain'],
                    what='COUNT(*) AS total',
                )

                resultOfRecords = self.conn.query(self.rawSQLOfRecords)
            except Exception, e:
                return (False, str(e))
        else:
            try:
                resultOfTotal = self.conn.select(
                    ['domain', 'domain_admins',],
                    what='COUNT(domain.domain) AS total',
                    where='domain.domain = domain_admins.domain AND domain_admins.username = %s' % (
                        web.sqlquote(self.admin),
                    ),
                )

                resultOfRecords = self.conn.query(self.rawSQLOfRecords)
            except Exception, e:
                return (False, str(e))

        if len(resultOfTotal) == 1:
            self.total = resultOfTotal[0].total or 0
        else:
            self.total = 0

        return (True, self.total, list(resultOfRecords),)

    @decorators.require_global_admin
    def delete(self, domains=[]):
        if not isinstance(domains, types.ListType):
            return (False, 'INVALID_DOMAIN_NAME')

        self.domains = [str(v).lower()
                        for v in domains
                        if iredutils.isDomain(v)
                       ]
        self.sql_domains = web.sqlquote(domains)

        # Delete domain and related records.
        try:
            self.conn.delete('alias', where='domain IN %s' % self.sql_domains)
            self.conn.delete(
                'alias_domain',
                where='alias_domain IN %s OR target_domain IN %s' % (self.sql_domains,self.sql_domains,),
            )
            self.conn.delete('domain_admins', where='domain IN %s' % self.sql_domains)
            self.conn.delete('mailbox', where='domain IN %s' % self.sql_domains)
            self.conn.delete('recipient_bcc_domain', where='domain IN %s' % self.sql_domains)
            self.conn.delete('recipient_bcc_user', where='domain IN %s' % self.sql_domains)
            self.conn.delete('sender_bcc_domain', where='domain IN %s' % self.sql_domains)
            self.conn.delete('sender_bcc_user', where='domain IN %s' % self.sql_domains)

            # Finally, delete from table `domain` to make sure all related
            # records were deleted.
            self.conn.delete('domain', where='domain IN %s' % self.sql_domains)

            for d in self.domains:
                web.logger(msg="Delete domain: %s." % (d), domain=d, event='delete',)
            return (True,)
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def simpleProfile(self, domain, columns=[]):
        self.domain = web.safestr(domain)

        if not iredutils.isDomain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        if len(columns) > 0:
            self.sql_what = ','.join(columns)
        else:
            self.sql_what = '*'

        try:
            qr = self.conn.select('domain',
                                  what=self.sql_what,
                                  where='domain=%s' % web.sqlquote(self.domain),
                                 )

            if len(qr) == 1:
                # Return first list element.
                return (True, list(qr)[0])
            else:
                return (False, 'NO_SUCH_OBJECT')
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def profile(self, domain):
        self.domain = web.safestr(domain)

        if not iredutils.isDomain(self.domain):
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
                    domain.domain = alias.domain
                    AND alias.address <> alias.goto
                    AND alias.address <> %s
                    )
                WHERE domain.domain=%s
                GROUP BY
                    domain.domain, domain.description, domain.aliases,
                    domain.mailboxes, domain.maxquota, domain.quota,
                    domain.transport, domain.backupmx, domain.created,
                    domain.active
                ORDER BY domain.domain
                LIMIT 1
                ''' % (web.sqlquote(self.domain),
                       web.sqlquote(self.domain),
                      )
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
        self.domain = web.safestr(data.get('domainName', '')).strip().lower()

        # Get company/organization name.
        self.cn = data.get('cn', '')

        # Check domain name.
        if not iredutils.isDomain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        # Check whether domain name already exist (domainName, domainAliasName).
        connutils = connUtils.Utils()
        if connutils.isDomainExists(self.domain):
            return (False, 'ALREADY_EXISTS')

        # Add domain in database.
        try:
            self.conn.insert(
                'domain',
                domain=self.domain,
                description=self.cn,
                transport=cfg.general.get('transport', 'dovecot'),
                created=iredutils.sqlNOW,
                active='1',
            )
            web.logger(msg="Create domain: %s." % (self.domain), domain=self.domain, event='create',)
        except Exception, e:
            return (False, str(e))

        return (True,)

    @decorators.require_domain_access
    def update(self, domain, profile_type, data,):
        self.profile_type = str(profile_type)
        self.domain = str(domain)

        # Pre-defined update key:value.
        updates = {'modified': iredutils.sqlNOW,}

        if self.profile_type == 'general':
            # Get name
            self.cn = data.get('cn', '')
            updates['description'] = self.cn

            # Get default quota for new user.
            self.defaultQuota = str(data.get('defaultQuota'))
            if self.defaultQuota.isdigit():
                updates['defaultuserquota'] = int(self.defaultQuota)

            if session.get('domainGlobalAdmin') is True:
                # Get account status
                if 'accountStatus' in data.keys():
                    updates['active'] = 1
                else:
                    updates['active'] = 0

                updates['maxquota'] = 0

                # Update SQL db with columns: maxquota, active.
                try:
                    self.conn.update(
                        'domain',
                        where='domain=%s' % web.sqlquote(self.domain),
                        **updates
                    )
                except Exception, e:
                    return (False, str(e))

                # Get list of domain admins.
                domainAdmins = [str(v).lower()
                                for v in data.get('domainAdmin', [])
                                if iredutils.isEmail(str(v))
                               ]

                try:
                    # Delete all records first.
                    self.conn.delete('domain_admins', where='domain=%s' % web.sqlquote(self.domain),)

                    # Add new admins.
                    if len(domainAdmins) > 0:
                        v = []
                        for adm in domainAdmins:
                            v += [{'username': adm,
                                  'domain': self.domain,
                                  'created': iredutils.sqlNOW,
                                  'active': 1,
                                 }]

                        self.conn.multiple_insert('domain_admins', values=v,)
                except Exception, e:
                    return (False, str(e))

        elif self.profile_type == 'bcc':
            # Delete old records first.
            try:
                self.conn.delete('sender_bcc_domain', where='domain=%s' % web.sqlquote(self.domain))
                self.conn.delete('recipient_bcc_domain', where='domain=%s' % web.sqlquote(self.domain))
            except Exception, e:
                return (False, str(e))

            # Get bcc status
            self.rbcc_status = '0'
            if 'recipientbcc' in data.keys():
                self.rbcc_status= '1'

            self.sbcc_status = '0'
            if 'senderbcc' in data.keys():
                self.sbcc_status= '1'

            senderBccAddress = str(data.get('senderBccAddress', None))
            if iredutils.isEmail(senderBccAddress):
                try:
                    self.conn.insert('sender_bcc_domain',
                                     domain=self.domain,
                                     bcc_address=senderBccAddress,
                                     created=iredutils.sqlNOW,
                                     active=self.sbcc_status
                                    )
                except Exception, e:
                    return (False, str(e))

            recipientBccAddress = str(data.get('recipientBccAddress', None))
            if iredutils.isEmail(recipientBccAddress):
                try:
                    self.conn.insert('recipient_bcc_domain',
                                     domain=self.domain,
                                     bcc_address=recipientBccAddress,
                                     created=iredutils.sqlNOW,
                                     active=self.rbcc_status
                                    )
                except Exception, e:
                    return (False, str(e))

        elif self.profile_type == 'relay':
            self.defaultTransport = str(cfg.general.get('mtaTransport', 'dovecot'))
            self.transport = data.get('mtaTransport', self.defaultTransport)
            updates['transport'] = self.transport
            self.conn.update(
                'domain',
                where='domain=%s' % web.sqlquote(self.domain),
                **updates
            )
        elif self.profile_type == 'catchall':
            # Delete old records first.
            try:
                self.conn.delete('alias', where='address=%s' % web.sqlquote(self.domain))
            except Exception, e:
                return (False, str(e))

            # Get list of destination addresses.
            catchallAddress = set([str(v).lower()
                                    for v in data.get('catchallAddress', '').split(',')
                                    if iredutils.isEmail(v)
                                  ])

            # Get enable/disable status.
            self.status = 0
            if 'accountStatus' in data.keys():
                self.status = 1

            if len(catchallAddress) > 0:
                try:
                    self.conn.insert(
                        'alias',
                        address=self.domain,
                        goto=','.join(catchallAddress),
                        domain=self.domain,
                        created=iredutils.sqlNOW,
                        active=self.status,
                    )
                except Exception, e:
                    return (False, str(e))
        elif self.profile_type == 'aliases':
            if session.get('domainGlobalAdmin') is True:
                # Delete old records first.
                try:
                    self.conn.delete('alias_domain', where='target_domain=%s' % web.sqlquote(self.domain))
                except Exception, e:
                    return (False, str(e))

                # Get domain aliases from web form and store in LDAP.
                aliasDomains = [str(v).lower()
                                for v in data.get('domainAliasName', [])
                                if iredutils.isDomain(v)
                               ]
                if len(aliasDomains) > 0:
                    v = []
                    for ad in aliasDomains:
                        v += [{'alias_domain': ad,
                               'target_domain': self.domain,
                               'created': iredutils.sqlNOW,
                               'active': 1,
                              }]
                    try:
                        self.conn.multiple_insert(
                            'alias_domain',
                            values=v,
                        )
                    except Exception, e:
                        return (False, str(e))

        elif self.profile_type == 'advanced':
            if session.get('domainGlobalAdmin') is True:
                numberOfUsers = str(data.get('numberOfUsers'))
                numberOfAliases = str(data.get('numberOfAliases'))
                minPwLen = str(data.get('minPasswordLength'))
                maxPwLen = str(data.get('maxPasswordLength'))

                if numberOfUsers.isdigit():
                    updates['mailboxes'] = int(numberOfUsers)

                if numberOfAliases.isdigit():
                    updates['aliases'] = int(numberOfAliases)

                if minPwLen.isdigit():
                    updates['minpasswordlength'] = int(minPwLen)

                if numberOfUsers.isdigit():
                    updates['maxpasswordlength'] = int(maxPwLen)

                defaultGroups = [str(v).lower()
                                 for v in data.get('defaultList', [])
                                 if iredutils.isEmail(v)
                                ]

                if len(defaultGroups) > 0:
                    updates['defaultuseraliases'] = ','.join(defaultGroups)

                try:
                    self.conn.update(
                        'domain',
                        where='domain=%s' % web.sqlquote(self.domain),
                        **updates
                    )
                except Exception, e:
                    return (False, str(e))

        return (True,)
