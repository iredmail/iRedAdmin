#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

import os, sys
from base64 import b64encode
import web
import ldap
from ldap.filter import escape_filter_chars
from libs.ldaplib import attrs

cfg = web.iredconfig
session = web.config.get('_session')

basedn = cfg.ldap['basedn']
domainadmin_dn = cfg.ldap['domainadmin_dn']

def convEmailToAdminDN(email):
    """Convert email address to ldap dn of mail domain admin."""
    email = str(email).strip()
    if len(email.split('@', 1)) == 2:
        user, domain = email.split('@', 1)
    else:
        return False


    # Admin DN format.
    # mail=user@domain.ltd,[LDAP_DOMAINADMIN_DN]
    dn = '%s=%s,%s' % ( attrs.USER_RDN, email, domainadmin_dn)

    return escape_filter_chars(dn)

def convEmailToUserDN(email):
    """Convert email address to ldap dn of normail mail user."""
    email = str(email).strip()
    if len(email.split('@', 1)) == 2:
        user, domain = email.split('@', 1)
    else:
        return False

    # User DN format.
    # mail=user@domain.ltd,domainName=domain.ltd,[LDAP_BASEDN]
    dn = '%s=%s,ou=Users,%s=%s,%s' % (
            attrs.USER_RDN, email,
            attrs.DOMAIN_RDN, domain,
            basedn)

    return escape_filter_chars(dn)

def convDomainToDN(domain):
    """Convert domain name to ldap dn."""
    domain = str(domain).strip().replace(' ', '')
    dn = attrs.DOMAIN_RDN + '=' + domain + ',' + basedn

    return escape_filter_chars(dn)

def extractValueFromDN(dn, attr):
    """Extract value of attribute from dn string."""
    dn = str(dn).strip().lower()
    attr = str(attr).strip().lower()

    for i in dn.split(','):
        if i.startswith(attr + '='):
            domain = i.split('=')[1]
            break
        else:
            domain = None

    return domain

def removeSpaceAndDot(string):
    """Remove leading and trailing dot and all whitespace."""
    return str(string).strip(' .').replace(' ', '')

# Sort LDAP query by dn.
# Note: this function deprecated since we use JavaScript to implement
# client-side sort.
def sortResults(attr='dn'):
    if attr == 'dn':
        comp = lambda x,y: cmp(x[0].lower(), y[0].lower())
    else:
        comp = lambda x,y: cmp(x[1][attr][0].lower(), y[1][attr][0].lower())

    return comp

# Generate attribute list & values from form data.
def get_mod_attrs(accountType, data):
    accountType = web.safestr('accountType')
    domainName = web.safestr(data.get('domainName', None))
    if domainName == 'None' or domainName == '':
        return False

    mod_attrs = []

    cn = data.get('cn', None)
    if cn is not None and cn != '':
        mod_attrs += [ ( ldap.MOD_REPLACE, 'cn', cn.encode('utf-8') ) ]

    # Get accountStatus.
    accountStatus = web.safestr(data.get('accountStatus', 'active'))
    if accountStatus not in attrs.VALUES_ACCOUNT_STATUS: accountStatus = 'active'
    mod_attrs += [ (ldap.MOD_REPLACE, 'accountStatus', accountStatus) ]

    if session.get('domainGlobalAdmin') == 'yes':
        # Convert to string, they don't contain non-ascii characters.

        # Get domain attributes.
        if accountType == 'domain':
            dn = convDomainToDN('domainName')

            domainBackupMX = web.safestr(data.get('domainBackupMX', 'no'))
            if domainBackupMX not in attrs.VALUES_DOMAIN_BACKUPMX: domainBackupMX = 'no'
            mod_attrs += [ (ldap.MOD_REPLACE, 'domainBackupMX', domainBackupMX) ]

            return {'dn': dn, 'mod_attrs': mod_attrs}

        elif accountType == 'user':
            pass
        elif accountType == 'maillist':
            pass
        elif accountType == 'alias':
            pass
    else:
        pass

# Generate hashed password from plain text.
def generatePasswd(password, pwscheme='SSHA'):
    pwscheme = pwscheme.upper()
    salt = os.urandom(8)
    if sys.version_info[1] < 5: # Python 2.5
        import sha
        if pwscheme == 'SSHA':
            h = sha.new(password)
            h.update(salt)
            hash = "{SSHA}" + b64encode( h.digest() + salt )
        else:
            hash = password
    else:
        import hashlib
        if pwscheme == 'SSHA':
            h = hashlib.sha1(password)
            h.update(salt)
            hash = "{SSHA}" + b64encode( h.digest() + salt )
        else:
            hash = password

    return hash
