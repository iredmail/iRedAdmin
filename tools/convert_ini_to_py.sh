#!/usr/bin/env bash

# Purpose: Convert old iRedAdmin config file (.ini format) to Python source
#          file format.

# Usage
[ X"$#" != X'1' ] && \
    echo "Usage: bash $0 /path/to/iredadmin/settings.ini" && \
    exit 255

# Old iRedAdmin-Pro
# config file
ini="$1"
[ ! -f ${ini} ] && echo "Error: File doesn't exist: ${ini}" && exit 255
# root directory
old_rootdir="$(dirname ${ini})"
# addition config file
old_local_setting_file="${old_rootdir}/libs/settings_local.py"

# Get root directory of current iRedAdmin-Pro.
rootdir="$(dirname $0)/.."
new_cfg="${rootdir}/settings.py"

# Check backend and copy sample config file.
backend="$(grep '^backend' ${ini} | awk '{print $3}')"
echo "* Backend: $backend"

echo "* Copy sample config file: ${rootdir}/settings.py.${backend}.sample"
cp ${rootdir}/settings.py.${backend}.sample ${new_cfg}

echo "* New config file: ${new_cfg}"

echo "  + Sync [general] section"
# Check webmaster
export ini_webmaster="$(grep '^webmaster' ${ini} | awk '{print $3}')"
perl -pi -e 's#^(webmaster = ).*#${1}"$ENV{ini_webmaster}"#' ${new_cfg}

# Ignore debug

# Check mail_error_to_webmaster
export ini_mail_error_to_webmaster="$(grep '^mail_error_to_webmaster' ${ini} | awk '{print $3}')"
if [ X"${ini_mail_error_to_webmaster}" == X'True' ]; then
    if grep '^MAIL_ERROR_TO_WEBMASTER' ${new_cfg} &>/dev/null; then
        perl -pi -e 's#^(MAIL_ERROR_TO_WEBMASTER).*#${1} = True#' ${new_cfg}
    else
        echo "MAIL_ERROR_TO_WEBMASTER = True" >> ${new_cfg}
    fi
fi

# Check lang
export ini_lang="$(grep '^lang' ${ini} | awk '{print $3}')"
perl -pi -e 's#^(default_language = ).*#${1}"$ENV{ini_lang}"#' ${new_cfg}

# Check storage_base_directory
export ini_storage_base_directory="$(grep '^storage_base_directory' ${ini} | awk '{print $3}')"
perl -pi -e 's#^(storage_base_directory = ).*#${1}"$ENV{ini_storage_base_directory}"#' ${new_cfg}

# Check default_mta_transport
export ini_default_mta_transport="$(grep '^mtaTransport' ${ini} | awk '{print $3}')"
perl -pi -e 's#^(default_mta_transport = ).*#${1}"$ENV{ini_default_mta_transport}"#' ${new_cfg}

# Ignore show_login_date

# Check min_passwd_length, max_passwd_length
export ini_min_passwd_length="$(grep '^min_passwd_length' ${ini} | awk '{print $3}')"
export ini_max_passwd_length="$(grep '^max_passwd_length' ${ini} | awk '{print $3}')"
perl -pi -e 's#^(min_passwd_length = ).*#${1}$ENV{ini_min_passwd_length}#' ${new_cfg}
perl -pi -e 's#^(max_passwd_length = ).*#${1}$ENV{ini_max_passwd_length}#' ${new_cfg}

# Check [iredadmin]
echo "  + Sync [iredadmin] section"
export ini_iredadmin_host="$(cat ${ini} | sed -n '/\[iredadmin\]/,/\[/ s/^host = *//p')"
export ini_iredadmin_port="$(cat ${ini} | sed -n '/\[iredadmin\]/,/\[/ s/^port = *//p')"
export ini_iredadmin_db="$(cat ${ini} | sed -n '/\[iredadmin\]/,/\[/ s/^db = *//p')"
export ini_iredadmin_user="$(cat ${ini} | sed -n '/\[iredadmin\]/,/\[/ s/^user = *//p')"
export ini_iredadmin_passwd="$(cat ${ini} | sed -n '/\[iredadmin\]/,/\[/ s/^passwd = *//p')"

perl -pi -e 's#^(iredadmin_db_host = ).*#${1}"$ENV{ini_iredadmin_host}"#' ${new_cfg}
perl -pi -e 's#^(iredadmin_db_port = ).*#${1}$ENV{ini_iredadmin_port}#' ${new_cfg}
perl -pi -e 's#^(iredadmin_db_name = ).*#${1}"$ENV{ini_iredadmin_db}"#' ${new_cfg}
perl -pi -e 's#^(iredadmin_db_user = ).*#${1}"$ENV{ini_iredadmin_user}"#' ${new_cfg}
perl -pi -e 's#^(iredadmin_db_password = ).*#${1}"$ENV{ini_iredadmin_passwd}"#' ${new_cfg}

# Check [vmaildb] for SQL backends
if [ X"${backend}" == X'ldap' ]; then
    echo "  + Sync [ldap] section"
    export ini_ldap_uri="$(cat ${ini} | sed -n '/\[ldap\]/,/\[/ s/^uri = *//p')"
    export ini_ldap_basedn="$(cat ${ini} | sed -n '/\[ldap\]/,/\[/ s/^basedn = *//p')"
    export ini_ldap_domainadmin_dn="$(cat ${ini} | sed -n '/\[ldap\]/,/\[/ s/^domainadmin_dn = *//p')"
    export ini_ldap_bind_dn="$(cat ${ini} | sed -n '/\[ldap\]/,/\[/ s/^bind_dn = *//p')"
    export ini_ldap_bind_pw="$(cat ${ini} | sed -n '/\[ldap\]/,/\[/ s/^bind_pw = *//p')"

    perl -pi -e 's#^(ldap_uri = ).*#${1}"$ENV{ini_ldap_uri}"#' ${new_cfg}
    perl -pi -e 's#^(ldap_basedn = ).*#${1}"$ENV{ini_ldap_basedn}"#' ${new_cfg}
    perl -pi -e 's#^(ldap_domainadmin_dn = ).*#${1}"$ENV{ini_ldap_domainadmin_dn}"#' ${new_cfg}
    perl -pi -e 's#^(ldap_bind_dn = ).*#${1}"$ENV{ini_ldap_bind_dn}"#' ${new_cfg}
    perl -pi -e 's#^(ldap_bind_password = ).*#${1}"$ENV{ini_ldap_bind_pw}"#' ${new_cfg}

elif [ X"${backend}" == X'mysql' -o X"${backend}" == X'pgsql' ]; then
    echo "  + Sync [vmaildb] section"
    export ini_vmaildb_host="$(cat ${ini} | sed -n '/\[vmaildb\]/,/\[/ s/^host = *//p')"
    export ini_vmaildb_port="$(cat ${ini} | sed -n '/\[vmaildb\]/,/\[/ s/^port = *//p')"
    export ini_vmaildb_db="$(cat ${ini} | sed -n '/\[vmaildb\]/,/\[/ s/^db = *//p')"
    export ini_vmaildb_user="$(cat ${ini} | sed -n '/\[vmaildb\]/,/\[/ s/^user = *//p')"
    export ini_vmaildb_passwd="$(cat ${ini} | sed -n '/\[vmaildb\]/,/\[/ s/^passwd = *//p')"

    perl -pi -e 's#^(vmail_db_host = ).*#${1}"$ENV{ini_vmaildb_host}"#' ${new_cfg}
    perl -pi -e 's#^(vmail_db_port = ).*#${1}$ENV{ini_vmaildb_port}#' ${new_cfg}
    perl -pi -e 's#^(vmail_db_name = ).*#${1}"$ENV{ini_vmaildb_db}"#' ${new_cfg}
    perl -pi -e 's#^(vmail_db_user = ).*#${1}"$ENV{ini_vmaildb_user}"#' ${new_cfg}
    perl -pi -e 's#^(vmail_db_password = ).*#${1}"$ENV{ini_vmaildb_passwd}"#' ${new_cfg}
fi

# Check [amavisd]
echo "  + Sync [amavisd] section"
export ini_amavisd_enable_logging="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^logging_into_sql = *//p')"
export ini_amavisd_host="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^host = *//p')"
export ini_amavisd_port="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^port = *//p')"
export ini_amavisd_db="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^db = *//p')"
export ini_amavisd_user="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^user = *//p')"
export ini_amavisd_passwd="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^passwd = *//p')"
export ini_amavisd_enable_quarantine="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^quarantine = *//p')"
export ini_amavisd_quarantine_port="$(cat ${ini} | sed -n '/\[amavisd\]/,/\[/ s/^quarantine_port = *//p')"

perl -pi -e 's#^(amavisd_enable_logging = ).*#${1}$ENV{ini_amavisd_enable_logging}#' ${new_cfg}
perl -pi -e 's#^(amavisd_db_host = ).*#${1}"$ENV{ini_amavisd_host}"#' ${new_cfg}
perl -pi -e 's#^(amavisd_db_port = ).*#${1}$ENV{ini_amavisd_port}#' ${new_cfg}
perl -pi -e 's#^(amavisd_db_name = ).*#${1}"$ENV{ini_amavisd_db}"#' ${new_cfg}
perl -pi -e 's#^(amavisd_db_user = ).*#${1}"$ENV{ini_amavisd_user}"#' ${new_cfg}
perl -pi -e 's#^(amavisd_db_password = ).*#${1}"$ENV{ini_amavisd_passwd}"#' ${new_cfg}
perl -pi -e 's#^(amavisd_enable_quarantine = ).*#${1}$ENV{ini_amavisd_enable_quarantine}#' ${new_cfg}
perl -pi -e 's#^(amavisd_quarantine_port = ).*#${1}$ENV{ini_amavisd_quarantine_port}#' ${new_cfg}

echo "* Checking addition custom settings: ${old_local_setting_file}"
if [ -f ${old_local_setting_file} ]; then
    cat ${old_local_setting_file} >> ${new_cfg}
    echo "  + Appended to new config file"
else
    echo "  + [SKIP] No such file."
fi

echo "* Set file owner (iredadmin:iredadmin) and permission (0400)."
chown iredadmin:iredadmin settings.py
chmod 0400 settings.py

echo "* DONE. New config file: ${new_cfg}"
