# Author: Zhang Huangbin <zhb@iredmail.org>

import web
from libs import iredutils
from libs.ldaplib import ldaputils

cfg = web.iredconfig

# Define and return LDIF structure of domain.
def ldif_maildomain(domain, cn=None,
        mtaTransport=cfg.general.get('mtaTransport', 'dovecot'),
        enabledService=['mail'], ):
    domain = web.safestr(domain).lower()

    minPasswordLength = cfg.general.get('min_passwd_length', '8')

    ldif = [
            ('objectClass',     ['mailDomain']),
            ('domainName',      [domain]),
            ('mtaTransport',    [mtaTransport]),
            ('accountStatus',   ['active']),
            ('enabledService',  enabledService),
            ('accountSetting',  ['minPasswordLength:%s' % minPasswordLength,]),
            ]

    ldif += ldaputils.getLdifOfSingleAttr(attr='cn', value=cn, default=domain,)

    return ldif

def ldif_group(name):
    ldif = [
            ('objectClass',     ['organizationalUnit']),
            ('ou',              [name]),
            ]

    return ldif


def ldif_mailExternalUser(mail,):
    mail = web.safestr(mail).lower()
    if not iredutils.isEmail(mail):
        return None

    listname, domain = mail.split('@')
    ldif = [
            ('objectClass',     ['mailExternalUser']),
            ('accountStatus',   ['active']),
            ('memberOfGroup',   [mail]),
            ('enabledService',  ['mail', 'deliver']),
            ]
    return ldif

# Define and return LDIF structure of domain admin.
def ldif_mailadmin(mail, passwd, cn, preferredLanguage='en_US', domainGlobalAdmin='no'):
    mail = web.safestr(mail).lower()

    ldif = [
            ('objectClass',     ['mailAdmin']),
            ('mail',            [mail]),
            ('userPassword',    [str(passwd)]),
            ('accountStatus',   ['active']),
            ('preferredLanguage', [web.safestr(preferredLanguage)]),
            ('domainGlobalAdmin',   ['yes']),
            ]

    ldif += ldaputils.getLdifOfSingleAttr(attr='cn', value=cn, default=mail.split('@', 1)[0],)

    return ldif

# Define and return LDIF structure of mail user.
# TODO Ability to assign account to groups.
def ldif_mailuser(domain, username, cn, passwd, quota=0, aliasDomains=[], groups=[],storageBaseDirectory=None,):
    domain = str(domain).lower()
    username = ldaputils.removeSpace(str(username)).lower()
    mail = username + '@' + domain

    if storageBaseDirectory is None:
        tmpStorageBaseDirectory = cfg.general.get('storage_base_directory').lower()
    else:
        tmpStorageBaseDirectory = storageBaseDirectory

    splitedSBD = tmpStorageBaseDirectory.rstrip('/').split('/')

    storageNode = splitedSBD.pop()
    storageBaseDirectory = '/'.join(splitedSBD)

    mailMessageStore =  storageNode + '/' + iredutils.setMailMessageStore(mail)
    homeDirectory = storageBaseDirectory + '/' + mailMessageStore

    # Generate basic LDIF.
    ldif = [
        ('objectClass',         ['inetOrgPerson', 'mailUser', 'shadowAccount', 'amavisAccount',]),
        ('mail',                [mail]),
        ('userPassword',        [str(passwd)]),
        ('sn',                  [username]),
        ('uid',                 [username]),
        ('storageBaseDirectory', [storageBaseDirectory]),
        ('mailMessageStore',    [mailMessageStore]),
        ('homeDirectory',       [homeDirectory]),
        ('accountStatus',       ['active']),
        ('enabledService',      ['mail', 'deliver', 'smtp', 'smtpsecured',
                                 'pop3', 'pop3secured', 'imap', 'imapsecured',
                                 'managesieve', 'managesievesecured',
                                 # ManageService name In dovecot-1.2.
                                 'sieve', 'sievesecured',
                                 'forward', 'senderbcc', 'recipientbcc',
                                 'internal',
                                 'shadowaddress', 'displayedInGlobalAddressBook',]),
        # Amavisd integration.
        ('amavisLocal',        ['TRUE']),
        ]

    # Append @shadowAddress.
    shadowAddresses = []
    for d in aliasDomains:
        if iredutils.isDomain(d):
            shadowAddresses += [username + '@' + d]

    if len(shadowAddresses) > 0:
        ldif += [('shadowAddress', shadowAddresses)]

    # Append quota. No 'mailQuota' attribute means unlimited.
    quota = str(quota).strip()
    if quota.isdigit():
        quota = int(quota) * 1024 * 1024
        ldif += [('mailQuota', [str(quota)])]

    # Append cn.
    ldif += ldaputils.getLdifOfSingleAttr(attr='cn', value=cn, default=username,)

    # Append groups.
    if isinstance(groups, list) and len(groups) >= 1:
        # Remove duplicate items.
        grps = set()
        for g in groups:
            grps.update([str(g).strip()])

        ldif += [('memberOfGroup', list(grps))]

    return ldif

# Define and return LDIF structure of catch-all account.
def ldif_catchall(domain, mailForwardingAddress=[],):
    domain = web.safestr(domain).lower()

    ldif = [
        ('objectClass',         ['inetOrgPerson', 'mailUser', ]),
        ('mail',                '@' + domain),
        ('accountStatus',       'active'),
        ('cn',                  'Catch-all account'),
        ('sn',                  'Catch-all account'),
        ('uid',                 'catchall'),
    ]

    catchallAddress = set([ web.safestr(v)
                            for v in mailForwardingAddress
                            if iredutils.isEmail(v)
                           ])

    if len(catchallAddress) > 0:
        ldif += [('mailForwardingAddress', list(catchallAddress))]

    return ldif
