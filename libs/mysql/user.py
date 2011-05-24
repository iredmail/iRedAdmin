# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import types
import web
from libs import iredutils
from libs.mysql import core, decorators, connUtils, domain as domainlib, admin as adminlib

cfg = web.iredconfig
session = web.config.get('_session', {})

ENABLED_SERVICES = ['enablesmtp', 'enablesmtpsecured',
                         'enablepop3', 'enablepop3secured',
                         'enableimap', 'enableimapsecured',
                         'enablemanagesieve', 'enablemanagesievesecured',
                         'enablesieve', 'enablesievesecured',
                         'enabledeliver', 'enableinternal',
                        ]

class User(core.MySQLWrap):
    def __del__(self):
        pass

    @decorators.require_domain_access
    @decorators.require_login
    def listAccounts(self, domain, cur_page=1):
        '''List all users.'''
        if not iredutils.isDomain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        self.domain = str(domain)

        # Pre-defined.
        self.total = 0

        try:
            resultOfTotal = self.conn.select(
                'mailbox',
                what='COUNT(username) AS total',
                where='domain=%s' % web.sqlquote(self.domain),
            )
            if len(resultOfTotal) == 1:
                self.total = resultOfTotal[0].total or 0

            resultOfRecords = self.conn.select(
                'mailbox',
                # Just query what we need to reduce memory use.
                what='username,name,quota,bytes,messages,employeeid,active,created',
                where='domain = %s' % web.sqlquote(self.domain),
                order='username ASC',
                limit=session['pageSizeLimit'],
                offset=(cur_page-1) * session['pageSizeLimit'],
            )

            return (True, self.total, list(resultOfRecords))
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def enableOrDisableAccount(self, domain, accounts, active=True):
        return self.setAccountStatus(accounts=accounts, active=active, accountType='user',)

    @decorators.require_domain_access
    def delete(self, domain, mails=[]):
        self.domain = str(domain)
        if not iredutils.isDomain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        if not isinstance(mails, types.ListType):
            return (False, 'INVALID_MAIL')

        self.mails = [str(v).lower() for v in mails if iredutils.isEmail(v) and str(v).endswith('@'+self.domain)]
        self.sqlMails = web.sqlquote(self.mails)

        # Delete domain and related records.
        try:
            self.conn.delete('mailbox', where='username IN %s' % self.sqlMails)
            self.conn.delete('alias', where='address IN %s' % self.sqlMails)
            self.conn.delete('recipient_bcc_user', where='username IN %s' % self.sqlMails)
            self.conn.delete('sender_bcc_user', where='username IN %s' % self.sqlMails)

            # TODO Remove email from alias.goto.
            #self.conn.delete()

            web.logger(
                msg="Delete user: %s." % ', '.join(self.mails),
                domain=self.domain,
                event='delete',
            )

            return (True,)
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def profile(self, domain, mail):
        self.mail = web.safestr(mail)
        self.domain = self.mail.split('@', 1)[-1]

        if self.domain != domain:
            return web.seeother('/domains?msg=PERMISSION_DENIED')

        if not self.mail.endswith('@' + self.domain):
            return web.seeother('/domains?msg=PERMISSION_DENIED')

        try:
            result = self.conn.query(
                '''
                SELECT
                    mailbox.*,
                    alias.address AS alias_address,
                    alias.goto AS alias_goto,
                    alias.active AS alias_active,
                    sbcc.username AS sbcc_username,
                    sbcc.bcc_address AS sbcc_bcc_address,
                    rbcc.username AS rbcc_username,
                    rbcc.bcc_address AS rbcc_bcc_address
                FROM mailbox
                LEFT JOIN alias ON (mailbox.username = alias.address)
                LEFT JOIN sender_bcc_user AS sbcc ON (mailbox.username = sbcc.username)
                LEFT JOIN recipient_bcc_user AS rbcc ON (mailbox.username = rbcc.username)
                WHERE mailbox.username = %s
                LIMIT 1
                ''' % web.sqlquote(self.mail)
            )
            return (True, list(result)[0])
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def add(self, domain, data):
        # Get domain name, username, cn.
        self.domain = web.safestr(data.get('domainName')).strip().lower()
        self.username = web.safestr(data.get('username')).strip().lower()
        self.mail = self.username + '@' + self.domain

        if self.domain != domain:
            return (False, 'PERMISSION_DENIED')

        if not iredutils.isDomain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        # Check account existing.
        connutils = connUtils.Utils()
        if connutils.isEmailExists(mail=self.mail):
            return (False, 'ALREADY_EXISTS')

        # Get domain profile.
        domainLib = domainlib.Domain()
        resultOfDomainProfile = domainLib.profile(domain=self.domain)

        if resultOfDomainProfile[0] is True:
            self.domainProfile = resultOfDomainProfile[1]
        else:
            return resultOfDomainProfile

        # Check account limit.
        adminLib = adminlib.Admin()
        numberOfExistAccounts = adminLib.getNumberOfManagedAccounts(accountType='user', domains=[self.domain])

        if self.domainProfile.mailboxes == 0:
            # Unlimited.
            pass
        elif self.domainProfile.mailboxes <= numberOfExistAccounts:
            return (False, 'EXCEEDED_DOMAIN_ACCOUNT_LIMIT')

        # Check spare quota and number of spare account limit.
        # Get quota from <form>
        self.mailQuota = str(data.get('mailQuota')).strip()
        self.defaultUserQuota = self.domainProfile.get('defaultuserquota', 0)

        if self.mailQuota.isdigit():
            self.mailQuota = int(self.mailQuota)
        else:
            self.mailQuota = self.defaultUserQuota

        # Re-calculate mail quota if this domain has limited max quota.
        if self.domainProfile.maxquota > 0:
            # Get used quota.
            qr = domainLib.getAllocatedQuotaSize(domain=self.domain)
            if qr[0] is True:
                self.allocatedQuota = qr[1]
            else:
                return qr

            spareQuota = self.domainProfile.maxquota - self.allocatedQuota

            if spareQuota > 0:
                if spareQuota < self.mailQuota:
                    self.mailQuota = spareQuota
            else:
                # No enough quota.
                return (False, 'EXCEEDED_DOMAIN_QUOTA_SIZE')

        #
        # Get password from <form>.
        #
        self.newpw = str(data.get('newpw', ''))
        self.confirmpw = str(data.get('confirmpw', ''))

        # Get password length limit from domain profile or global setting.
        self.minPasswordLength = self.domainProfile.get('minpasswordlength',cfg.general.get('min_passwd_length', '0'))
        self.maxPasswordLength = self.domainProfile.get('maxpasswordlength', cfg.general.get('max_passwd_length', '0'))

        resultOfPW = iredutils.verifyNewPasswords(
            self.newpw,
            self.confirmpw,
            min_passwd_length=self.minPasswordLength,
            max_passwd_length=self.maxPasswordLength,
        )
        if resultOfPW[0] is True:
            self.passwd = iredutils.getSQLPassword(resultOfPW[1])
        else:
            return resultOfPW

        # Get display name from <form>
        self.cn = data.get('cn', '')

        # Assign new user to default mail aliases.
        assignedAliases = [str(v).lower()
                           for v in str(self.domainProfile.defaultuseraliases).split(',')
                           if iredutils.isEmail(v)
                          ]

        try:
            # Store new user in SQL db.
            self.conn.insert(
                'mailbox',
                domain=self.domain,
                username=self.mail,
                password=self.passwd,
                name=self.cn,
                maildir=iredutils.setMailMessageStore(self.mail),
                quota=self.mailQuota,
                created=iredutils.sqlNOW,
                active='1',
                local_part=self.username,
            )

            # Assign new user to default mail aliases.
            if len(assignedAliases) > 0:
                for ali in assignedAliases:
                    try:
                        self.conn.query(
                            '''
                            UPDATE alias
                            SET goto=CONCAT(goto, %s)
                            WHERE address=%s AND domain=%s
                            ''' % (
                                web.sqlquote(','+self.mail),
                                web.sqlquote(ali),
                                web.sqlquote(self.domain),
                            )
                        )
                    except:
                        pass

            web.logger(msg="Create user: %s." % (self.mail), domain=self.domain, event='create',)
            return (True,)
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def update(self, profile_type, mail, data):
        self.profile_type = web.safestr(profile_type)
        self.mail = str(mail).lower()
        self.domain = self.mail.split('@', 1)[-1]

        # Pre-defined update key:value.
        updates = {'modified': iredutils.sqlNOW,}

        if self.profile_type == 'general':
            # Get name
            self.cn = data.get('cn', '')
            updates['name'] = self.cn

            # Get account status
            if 'accountStatus' in data.keys():
                updates['active'] = 1
            else:
                updates['active'] = 0

            # Get mail quota size.
            mailQuota = str(data.get('mailQuota'))
            if mailQuota.isdigit():
                updates['quota'] = int(mailQuota)

            # Get employee id.
            employeeNumber = data.get('employeeNumber', '')
            updates['employeeid'] = employeeNumber

            aliases = [str(v).lower()
                       for v in data.get('memberOfAlias', [])
                       if iredutils.isEmail(v)
                       and str(v).endswith('@'+self.domain)
                      ]

        elif self.profile_type == 'forwarding':
            mailForwardingAddress = [str(v).lower()
                                     for v in data.get('mailForwardingAddress', [])
                                     if iredutils.isEmail(v)
                                    ]

            if self.mail in mailForwardingAddress:
                mailForwardingAddress.remove(self.mail)

            try:
                self.conn.delete('alias', where='address=%s' % web.sqlquote(self.mail))
            except Exception, e:
                return (False, str(e))

            inserts = {}
            if len(mailForwardingAddress) > 0:
                # Get account status
                if 'forwarding' in data.keys():
                    inserts['active'] = 1
                else:
                    inserts['active'] = 0

                if 'savecopy' in data.keys():
                    mailForwardingAddress += [self.mail]

                inserts['goto'] = ','.join(mailForwardingAddress)

                inserts['address'] = self.mail
                inserts['domain'] = self.domain
                inserts['created'] = iredutils.sqlNOW
                inserts['active'] = 1

                try:
                    self.conn.insert(
                        'alias',
                        **inserts
                    )
                    return (True,)
                except Exception, e:
                    return (False, str(e))
            else:
                return (True,)

        elif self.profile_type == 'password':
            self.newpw = str(data.get('newpw', ''))
            self.confirmpw = str(data.get('confirmpw', ''))

            # Verify new passwords.
            qr = iredutils.verifyNewPasswords(self.newpw, self.confirmpw)
            if qr[0] is True:
                self.passwd = iredutils.getSQLPassword(qr[1])
            else:
                return qr

            # Hash/encrypt new password.
            updates['password'] = self.passwd

        elif self.profile_type == 'advanced':
            # Get enabled services.
            self.enabledService = [str(v).lower()
                                   for v in data.get('enabledService', [])
                                   if v in ENABLED_SERVICES
                                  ]
            self.disabledService = [v for v in ENABLED_SERVICES if v not in self.enabledService]

            # Append 'sieve', 'sievesecured' for dovecot-1.2.
            if 'enablemanagesieve' in self.enabledService:
                self.enabledService += ['enablesieve']
            else:
                self.disabledService += ['enablesieve']

            if 'enablemanagesievesecured' in self.enabledService:
                self.enabledService += ['enablesievesecured']
            else:
                self.disabledService += ['enablesievesecured']

            # Enable/disable services.
            for srv in self.enabledService:
                updates[srv] = 1

            for srv in self.disabledService:
                updates[srv] = 0

            if session.get('domainGlobalAdmin') is True:
                # Get maildir related settings.
                self.storagebasedirectory = str(data.get('storageBaseDirectory', ''))
                self.storagenode = str(data.get('storageNode', ''))
                self.maildir = str(data.get('mailMessageStore', ''))

                updates['storagebasedirectory'] = self.storagebasedirectory
                updates['storagenode'] = self.storagenode
                updates['maildir'] = self.maildir

                # Get transport.
                self.defaultTransport = str(cfg.general.get('mtaTransport', 'dovecot'))
                self.transport = str(data.get('mtaTransport', self.defaultTransport))
                updates['transport'] = self.transport

            # Get sender/recipient bcc.
            senderBccAddress = str(data.get('senderBccAddress', ''))
            recipientBccAddress = str(data.get('recipientBccAddress', ''))

            updates_sender_bcc = {}
            updates_recipient_bcc = {}
            if iredutils.isEmail(senderBccAddress):
                updates_sender_bcc = {'username': self.mail,
                                      'bcc_address': senderBccAddress,
                                      'domain': self.domain,
                                      'created': iredutils.sqlNOW,
                                      'active': 1,
                                     }

            if iredutils.isEmail(recipientBccAddress):
                updates_recipient_bcc = {'username': self.mail,
                                         'bcc_address': recipientBccAddress,
                                         'domain': self.domain,
                                         'created': iredutils.sqlNOW,
                                         'active': 1,
                                        }

            try:
                # Delete bcc records first.
                self.conn.delete('sender_bcc_user', where='username=%s' % web.sqlquote(self.mail))
                self.conn.delete('recipient_bcc_user', where='username=%s' % web.sqlquote(self.mail))

                # Insert new records.
                if updates_sender_bcc:
                    self.conn.insert('sender_bcc_user', **updates_sender_bcc)

                if updates_recipient_bcc:
                    self.conn.insert('recipient_bcc_user', **updates_recipient_bcc)
            except Exception, e:
                return (False, str(e))

        else:
            return (True,)

        # Update SQL db with columns: maxquota, active.
        try:
            self.conn.update(
                'mailbox',
                where='username=%s AND domain=%s' % (
                    web.sqlquote(self.mail),
                    web.sqlquote(self.domain),
                ),
                **updates
            )
            return (True,)
        except Exception, e:
            return (False, str(e))
