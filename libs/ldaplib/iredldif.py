# Author: Zhang Huangbin <zhb@iredmail.org>

import web
import settings
from libs import iredutils
from libs.ldaplib import ldaputils


# Define and return LDIF structure of domain.
def ldif_maildomain(domain,
                    cn=None,
                    mtaTransport=settings.default_mta_transport,
                    enabledService=['mail']):
    domain = web.safestr(domain).lower()

    minPasswordLength = settings.min_passwd_length

    ldif = [('objectClass', ['mailDomain']),
            ('domainName', [domain]),
            ('mtaTransport', [mtaTransport]),
            ('accountStatus', ['active']),
            ('enabledService', enabledService),
            ('accountSetting', ['minPasswordLength:%s' % minPasswordLength])]

    ldif += ldaputils.get_ldif_of_attr(attr='cn', value=cn, default=domain)

    return ldif


def ldif_group(name):
    ldif = [('objectClass', ['organizationalUnit']),
            ('ou', [name])]

    return ldif


def ldif_mailExternalUser(mail):
    mail = web.safestr(mail).lower()
    if not iredutils.is_email(mail):
        return None

    listname, domain = mail.split('@')
    ldif = [('objectClass', ['mailExternalUser']),
            ('accountStatus', ['active']),
            ('memberOfGroup', [mail]),
            ('enabledService', ['mail', 'deliver'])]

    return ldif


# Define and return LDIF structure of domain admin.
def ldif_mailadmin(mail,
                   passwd,
                   cn,
                   preferredLanguage='en_US',
                   domainGlobalAdmin='no'):
    mail = web.safestr(mail).lower()

    ldif = [('objectClass', ['mailAdmin']),
            ('mail', [mail]),
            ('userPassword', [str(passwd)]),
            ('accountStatus', ['active']),
            ('preferredLanguage', [web.safestr(preferredLanguage)]),
            ('domainGlobalAdmin', [web.safestr(domainGlobalAdmin)])]

    ldif += ldaputils.get_ldif_of_attr(attr='cn',
                                       value=cn,
                                       default=mail.split('@', 1)[0])

    return ldif


# Define and return LDIF structure of mail user.
def ldif_mailuser(domain,
                  username,
                  cn,
                  passwd,
                  quota=0,
                  aliasDomains=None,
                  groups=None,
                  storageBaseDirectory=None):
    domain = str(domain).lower()
    username = str(username).strip().replace(' ', '').lower()
    mail = username + '@' + domain

    if storageBaseDirectory is None:
        tmpStorageBaseDirectory = settings.storage_base_directory.lower()
    else:
        tmpStorageBaseDirectory = storageBaseDirectory

    splitedSBD = tmpStorageBaseDirectory.rstrip('/').split('/')

    storageNode = splitedSBD.pop()
    storageBaseDirectory = '/'.join(splitedSBD)

    mailMessageStore = storageNode + '/' + iredutils.generate_maildir_path(mail)
    homeDirectory = storageBaseDirectory + '/' + mailMessageStore

    # Generate basic LDIF.
    ldif = [
        ('objectClass', ['inetOrgPerson', 'mailUser', 'shadowAccount', 'amavisAccount']),
        ('mail', [mail]),
        ('userPassword', [str(passwd)]),
        ('sn', [username]),
        ('uid', [username]),
        ('storageBaseDirectory', [storageBaseDirectory]),
        ('mailMessageStore', [mailMessageStore]),
        ('homeDirectory', [homeDirectory]),
        ('accountStatus', ['active']),
        ('enabledService', ['mail', 'deliver', 'lda', 'lmtp', 'smtp', 'smtpsecured',
                            'pop3', 'pop3secured', 'imap', 'imapsecured',
                            'managesieve', 'managesievesecured',
                            'sogo',
                            # ManageService name In dovecot-1.2.
                            'sieve', 'sievesecured',
                            'forward', 'senderbcc', 'recipientbcc',
                            'internal', 'lib-storage', 'indexer-worker', 'doveadm',
                            'dsync',
                            'shadowaddress', 'displayedInGlobalAddressBook']),
        # shadowAccount integration.
        ('shadowLastChange', ['0']),
        # Amavisd integration.
        ('amavisLocal', ['TRUE'])]

    # Append `shadowAddress`
    if aliasDomains:
        _shadowAddresses = [username + '@' + d for d in aliasDomains if iredutils.is_domain(d)]
        ldif += [('shadowAddress', _shadowAddresses)]

    # Append quota. No 'mailQuota' attribute means unlimited.
    quota = str(quota).strip()
    if quota.isdigit():
        quota = int(quota) * 1024 * 1024
        ldif += [('mailQuota', [str(quota)])]

    # Append cn.
    ldif += ldaputils.get_ldif_of_attr(attr='cn',
                                       value=cn,
                                       default=username)

    # Append groups.
    if groups and isinstance(groups, list):
        # Remove duplicate items.
        grps = [str(g).strip() for g in groups]
        ldif += [('memberOfGroup', list(set(grps)))]

    return ldif
