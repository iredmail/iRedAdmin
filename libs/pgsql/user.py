# encoding: utf-8

# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils
from libs.pgsql import core, decorators, connUtils, domain as domainlib, admin as adminlib

session = web.config.get('_session', {})

ENABLED_SERVICES = [
    'enablesmtp', 'enablesmtpsecured',
    'enablepop3', 'enablepop3secured',
    'enableimap', 'enableimapsecured',
    'enablemanagesieve', 'enablemanagesievesecured',
    'enablesieve', 'enablesievesecured',
    'enabledeliver', 'enableinternal',
    'enablesogo',
]


class User(core.PGSQLWrap):
    def __del__(self):
        pass

    @decorators.require_domain_access
    @decorators.require_login
    def listAccounts(self, domain, cur_page=1):
        '''List all users.'''
        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        domain = str(domain)
        connutils = connUtils.Utils()
        if not connutils.is_domain_exists(domain):
            return (False, 'PERMISSION_DENIED')

        # Pre-defined.
        sql_vars = {'domain': domain, }
        total = 0

        try:
            resultOfTotal = self.conn.select(
                'mailbox',
                vars=sql_vars,
                what='COUNT(username) AS total',
                where='domain=$domain',
            )
            if len(resultOfTotal) == 1:
                total = resultOfTotal[0].total or 0

            resultOfRecords = self.conn.select(
                'mailbox',
                vars=sql_vars,
                # Just query what we need to reduce memory use.
                what='username,name,quota,employeeid,active',
                where='domain=$domain',
                order='username ASC',
                limit=settings.PAGE_SIZE_LIMIT,
                offset=(cur_page - 1) * settings.PAGE_SIZE_LIMIT,
            )

            return (True, total, list(resultOfRecords))
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def enableOrDisableAccount(self, domain, accounts, active=True):
        return self.setAccountStatus(accounts=accounts, active=active, accountType='user')

    @decorators.require_domain_access
    def delete(self, domain, mails=None, keep_mailbox_days=0):
        domain = str(domain).lower()

        if not iredutils.is_domain(domain):
            return (False, 'INVALID_DOMAIN_NAME')

        if not mails:
            return (False, 'INVALID_MAIL')

        mails = [str(v).lower()
                 for v in mails
                 if iredutils.is_email(v) and str(v).endswith('@' + domain)]

        if not mails:
            return (False, 'INVALID_MAIL')

        # Delete user and related records.
        try:
            qr = self.deleteAccounts(accounts=mails, accountType='user', keep_mailbox_days=keep_mailbox_days)
            if qr[0] is True:
                web.logger(
                    msg="Delete user: %s." % ', '.join(mails),
                    domain=domain,
                    event='delete',
                )
            else:
                return qr

            return (True,)
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def profile(self, domain, mail):
        self.mail = web.safestr(mail)
        self.domain = self.mail.split('@', 1)[-1]

        if self.domain != domain:
            raise web.seeother('/domains?msg=PERMISSION_DENIED')

        if not self.mail.endswith('@' + self.domain):
            raise web.seeother('/domains?msg=PERMISSION_DENIED')

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
                sbcc.active AS sbcc_active,
                rbcc.username AS rbcc_username,
                rbcc.bcc_address AS rbcc_bcc_address,
                rbcc.active AS rbcc_active
                FROM mailbox
                LEFT JOIN alias ON (mailbox.username = alias.address)
                LEFT JOIN sender_bcc_user AS sbcc ON (mailbox.username = sbcc.username)
                LEFT JOIN recipient_bcc_user AS rbcc ON (mailbox.username = rbcc.username)
                WHERE mailbox.username = $username
                LIMIT 1
                ''',
                vars={'username': self.mail, },
            )
            if result:
                return (True, list(result)[0])
            else:
                return (False, 'INVALID_MAIL')
        except Exception, e:
            return (False, str(e))

    @decorators.require_domain_access
    def add(self, domain, data):
        # Get domain name, username, cn.
        self.domain = web.safestr(data.get('domainName')).strip().lower()
        mail_local_part = web.safestr(data.get('username')).strip().lower()
        self.mail = mail_local_part + '@' + self.domain

        if not iredutils.is_domain(self.domain):
            return (False, 'INVALID_DOMAIN_NAME')

        if self.domain != domain:
            return (False, 'PERMISSION_DENIED')

        if not iredutils.is_email(self.mail):
            return (False, 'INVALID_MAIL')

        # Check account existing.
        connutils = connUtils.Utils()
        if connutils.is_email_exists(mail=self.mail):
            return (False, 'ALREADY_EXISTS')

        # Get domain profile.
        domainLib = domainlib.Domain()
        resultOfDomainProfile = domainLib.profile(domain=self.domain)

        if resultOfDomainProfile[0] is True:
            domainProfile = resultOfDomainProfile[1]
        else:
            return resultOfDomainProfile

        # Check account limit.
        adminLib = adminlib.Admin()
        numberOfExistAccounts = adminLib.getNumberOfManagedAccounts(accountType='user', domains=[self.domain])

        if domainProfile.mailboxes == -1:
            return (False, 'NOT_ALLOWED')
        elif domainProfile.mailboxes > 0:
            if domainProfile.mailboxes <= numberOfExistAccounts:
                return (False, 'EXCEEDED_DOMAIN_ACCOUNT_LIMIT')

        # Check spare quota and number of spare account limit.
        # Get quota from <form>
        mailQuota = str(data.get('mailQuota')).strip()

        if mailQuota.isdigit():
            mailQuota = int(mailQuota)
        else:
            mailQuota = 0

        # Re-calculate mail quota if this domain has limited max quota.
        if domainProfile.maxquota > 0:
            # Get used quota.
            qr = domainLib.getAllocatedQuotaSize(domain=self.domain)
            if qr[0] is True:
                allocatedQuota = qr[1]
            else:
                return qr

            spareQuota = domainProfile.maxquota - allocatedQuota

            if spareQuota > 0:
                if spareQuota < mailQuota:
                    mailQuota = spareQuota
            else:
                # No enough quota.
                return (False, 'EXCEEDED_DOMAIN_QUOTA_SIZE')

        #
        # Get password from <form>.
        #
        newpw = web.safestr(data.get('newpw', ''))
        confirmpw = web.safestr(data.get('confirmpw', ''))

        resultOfPW = iredutils.verify_new_password(
            newpw,
            confirmpw,
            min_passwd_length=settings.min_passwd_length,
            max_passwd_length=settings.max_passwd_length,
        )
        if resultOfPW[0] is True:
            pwscheme = None
            if 'storePasswordInPlainText' in data and settings.STORE_PASSWORD_IN_PLAIN_TEXT:
                pwscheme = 'PLAIN'
            passwd = iredutils.generate_password_hash(resultOfPW[1], pwscheme=pwscheme)
        else:
            return resultOfPW

        # Get display name from <form>
        cn = data.get('cn', '')

        # Get storage base directory.
        tmpStorageBaseDirectory = settings.storage_base_directory.lower()
        splitedSBD = tmpStorageBaseDirectory.rstrip('/').split('/')
        storageNode = splitedSBD.pop()
        storageBaseDirectory = '/'.join(splitedSBD)

        try:
            # Store new user in SQL db.
            self.conn.insert(
                'mailbox',
                domain=self.domain,
                username=self.mail,
                password=passwd,
                name=cn,
                maildir=iredutils.generate_maildir_path(self.mail),
                quota=mailQuota,
                storagebasedirectory=storageBaseDirectory,
                storagenode=storageNode,
                created=iredutils.get_gmttime(),
                active='1',
                local_part=mail_local_part,
            )

            # Create an alias account: address=goto.
            self.conn.insert(
                'alias',
                address=self.mail,
                goto=self.mail,
                domain=self.domain,
                created=iredutils.get_gmttime(),
                active='1',
            )

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
        updates = {'modified': iredutils.get_gmttime()}

        if self.profile_type == 'general':
            # Get settings of domain admin and global admin
            managed_domain = ''
            if 'domainadmin' in data:
                # isadmin=1
                updates['isadmin'] = 1
                managed_domain = self.domain
            else:
                updates['isadmin'] = 0

            if session.get('domainGlobalAdmin'):
                if 'domainGlobalAdmin' in data:
                    updates['isadmin'] = 1
                    updates['isglobaladmin'] = 1
                    managed_domain = 'ALL'
                else:
                    updates['isglobaladmin'] = 0

            # Delete records in domain_admins first
            self.conn.delete('domain_admins',
                             vars={'username': self.mail},
                             where='username=$username')

            if updates.get('isadmin') == 1:
                try:
                    self.conn.insert('domain_admins',
                                     username=self.mail,
                                     domain=managed_domain,
                                     created=iredutils.get_gmttime(),
                                     active=1)
                except:
                    pass

            # Get name
            cn = data.get('cn', '')
            updates['name'] = cn

            # Get preferred language: short lang code. e.g. en_US, de_DE.
            preferred_lang = web.safestr(data.get('preferredLanguage', 'en_US'))
            # Must be equal to or less than 5 characters.
            if len(preferred_lang) > 5:
                preferred_lang = preferred_lang[:5]
            updates['language'] = preferred_lang
            # Update language immediately.
            if session.get('username') == self.mail and \
               session.get('lang', 'en_US') != preferred_lang:
                session['lang'] = preferred_lang

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

        elif self.profile_type == 'password':
            newpw = str(data.get('newpw', ''))
            confirmpw = str(data.get('confirmpw', ''))

            # Verify new passwords.
            qr = iredutils.verify_new_password(newpw, confirmpw)
            if qr[0] is True:
                pwscheme = None
                if 'storePasswordInPlainText' in data and settings.STORE_PASSWORD_IN_PLAIN_TEXT:
                    pwscheme = 'PLAIN'
                passwd = iredutils.generate_password_hash(qr[1], pwscheme=pwscheme)
            else:
                return qr

            # Hash/encrypt new password.
            updates['password'] = passwd

            # Update password last change date in column: passwordlastchange.
            #
            # Old iRedMail version doesn't have column mailbox.passwordlastchange,
            # so we update it with a seperate SQL command with exception handle.
            try:
                self.conn.update(
                    'mailbox',
                    vars={'username': self.mail, },
                    where='username=$username',
                    passwordlastchange=iredutils.get_gmttime(),
                )
            except:
                pass

        else:
            return (True,)

        # Update SQL db
        try:
            self.conn.update(
                'mailbox',
                vars={'username': self.mail, 'domain': self.domain, },
                where='username=$username AND domain=$domain',
                **updates
            )

            # Update session immediately after updating SQL.
            if profile_type == 'general':
                if 'domainGlobalAdmin' not in data and \
                   session.get('username') == self.mail:
                    session['domainGlobalAdmin'] = False

            return (True,)
        except Exception, e:
            return (False, str(e))
