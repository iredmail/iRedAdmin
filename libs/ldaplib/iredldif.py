#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import time
import web
from libs.ldaplib import ldaputils

cfg = web.iredconfig

# Define and return LDIF structure of domain.
def ldif_maildomain(domain, cn=None,
        mtaTransport=cfg.general.get('mtaTransport', 'dovecot'),
        enabledService=['mail'], ):
    domain = web.safestr(domain).lower()
    ldif = [
            ('objectCLass',     ['mailDomain']),
            ('domainName',      [domain]),
            ('mtaTransport',    [mtaTransport]),
            ('accountStatus',   ['active']),
            ('enabledService',  enabledService),
            ]

    ldif += ldaputils.getSingleLDIF(attr='cn', value=cn, default=domain,)

    return ldif

def ldif_group(name):
    ldif = [
            ('objectClass',     ['organizationalUnit']),
            ('ou',              [name]),
            ]

    return ldif

def ldif_group_alias():
    ldif = [
            ('objectClass',     ['organizationalUnit']),
            ('ou',              ['Aliases']),
            ]

    return ldif

def ldif_maillist(group, domain, cn=u'Mail Group', desc=u'Mail Group',):
    group=str(group)
    domain=str(domain)

    ldif = [
            ('objectClass',     'mailList'),
            ('accountStatus',   'active'),
            ('mail',            group + '@' + domain),
            ('hasMember',       'no'),
            ]

    ldif += ldaputils.getSingleLDIF(attr='cn', value=cn, default=group)

    if desc is not None:
        ldif += [('description', desc.encode('utf-8'))]

    return ldif

# Define and return LDIF structure of domain admin.
def ldif_mailadmin(mail, passwd, cn, preferredLanguage='en_US', domainGlobalAdmin='yes'):
    mail = web.safestr(mail)

    ldif = [
            ('objectCLass',     ['mailAdmin']),
            ('mail',            [mail]),
            ('userPassword',    [str(passwd)]),
            ('accountStatus',   ['active']),
            ('preferredLanguage', [web.safestr(preferredLanguage)]),
            ('domainGlobalAdmin',   [web.safestr(domainGlobalAdmin)]),
            ]

    ldif += ldaputils.getSingleLDIF(attr='cn', value=cn, default=mail.split('@', 1)[0])

    return ldif

# Define and return LDIF structure of mail user.
def ldif_mailuser(domain, username, cn, passwd, quota=cfg.general.get('default_quota')):
    DATE = time.strftime('%Y.%m.%d.%H.%M.%S')
    domain = str(domain).lower()
    quota = int(quota) * 1024 * 1024
    username = ldaputils.removeSpaceAndDot(str(username)).lower()
    mail = username + '@' + domain
    #dn = convEmailToUserDN(mail)

    if eval(cfg.general.get('hashed_maildir', True)) is True:
        if len(username) >= 3:
            maildir_user = "%s/%s/%s/%s-%s/" % (username[:1], username[:2], username[:3], username, DATE,)
        elif len(username) == 2:
            maildir_user = "%s/%s/%s/%s-%s/" % (
                    username[:1],
                    username[:],
                    username[:] + username[-1],
                    username,
                    DATE,
                    )
        else:
            maildir_user = "%s/%s/%s/%s-%s/" % (
                    username[0],
                    username[0] * 2,
                    username[0] * 3,
                    username,
                    DATE,
                    )
        mailMessageStore = domain + '/' + maildir_user
    else:
        mailMessageStore = "%s/%s-%s/" % (domain, username, DATE,)

    mailMessageStore = mailMessageStore.lower()
    storageBaseDirectory = cfg.general.get('storage_base_directory').lower()
    homeDirectory = storageBaseDirectory + '/' + mailMessageStore

    ldif = [
        ('objectCLass',         ['inetOrgPerson', 'mailUser', 'shadowAccount']),
        ('mail',                [mail]),
        ('userPassword',        [str(passwd)]),
        ('mailQuota',           [str(quota)]),
        ('sn',                  [username]),
        ('uid',                 [username]),
        ('storageBaseDirectory', [storageBaseDirectory]),
        ('mailMessageStore',    [mailMessageStore]),
        ('homeDirectory',       [homeDirectory]),
        ('accountStatus',       ['active']),
        ('mtaTransport',        ['dovecot']),
        ('enabledService',      ['mail', 'smtp', 'pop3', 'imap', 'deliver', 'forward',
                                'senderbcc', 'recipientbcc', 'managesieve',
                                'displayedInGlobalAddressBook',]),
        ('memberOfGroup',       ['all@'+domain]), # Make all users belong to group 'all@domain.ltd'.
        ]

    ldif += ldaputils.getSingleLDIF(attr='cn', value=cn, default=username)

    return ldif
