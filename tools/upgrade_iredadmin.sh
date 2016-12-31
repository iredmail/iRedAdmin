#!/usr/bin/env bash

# Purpose: Upgrade iRedAdmin from old release.
#          Works with both iRedAdmin open souce edition or iRedAdmin-Pro.

# USAGE:
#
#   # cd /path/to/iRedAdmin-xxx/tools/
#   # bash upgrade_iredadmin.sh

export IRA_HTTPD_USER='iredadmin'
export IRA_HTTPD_GROUP='iredadmin'

export SYS_ROOT_USER='root'

# Check OS to detect some necessary info.
export KERNEL_NAME="$(uname -s | tr '[a-z]' '[A-Z]')"
export UWSGI_RC_SCRIPT_NAME='uwsgi'
export NGINX_PID_FILE='/var/run/nginx.pid'

if [ X"${KERNEL_NAME}" == X"LINUX" ]; then
    export PYTHON_BIN='/usr/bin/python'

    if [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        export DISTRO='RHEL'
        export HTTPD_SERVERROOT='/var/www'
        export HTTPD_RC_SCRIPT_NAME='httpd'
        export CRON_SPOOL_DIR='/var/spool/cron'
    elif [ -f /etc/lsb-release ]; then
        # Ubuntu
        export DISTRO='UBUNTU'
        if [ -d '/opt/www' ]; then
            export HTTPD_SERVERROOT='/opt/www'
        else
            export HTTPD_SERVERROOT='/usr/share/apache2'
        fi
        export HTTPD_RC_SCRIPT_NAME='apache2'
        export CRON_SPOOL_DIR='/var/spool/cron/crontabs'
    elif [ -f /etc/debian_version ]; then
        # Debian
        export DISTRO='DEBIAN'
        if [ -d '/opt/www' ]; then
            export HTTPD_SERVERROOT='/opt/www'
        else
            export HTTPD_SERVERROOT='/usr/share/apache2'
        fi
        export HTTPD_RC_SCRIPT_NAME='apache2'
        export CRON_SPOOL_DIR='/var/spool/cron/crontabs'
    elif [ -f /etc/SuSE-release ]; then
        # openSUSE
        export DISTRO='SUSE'
        export HTTPD_SERVERROOT='/srv/www'
        export HTTPD_RC_SCRIPT_NAME='apache2'
        export CRON_SPOOL_DIR='/var/spool/cron'
    else
        echo "<<< ERROR >>> Cannot detect Linux distribution name. Exit."
        echo "Please contact support@iredmail.org to solve it."
        exit 255
    fi
elif [ X"${KERNEL_NAME}" == X'FREEBSD' ]; then
    export DISTRO='FREEBSD'
    export HTTPD_SERVERROOT='/usr/local/www'
    export PYTHON_BIN='/usr/local/bin/python'
    if [ -f /usr/local/etc/rc.d/apache24 ]; then
        export HTTPD_RC_SCRIPT_NAME='apache24'
    else
        export HTTPD_RC_SCRIPT_NAME='apache22'
    fi
    export CRON_SPOOL_DIR='/var/cron/tabs'
elif [ X"${KERNEL_NAME}" == X'OPENBSD' ]; then
    export PYTHON_BIN='/usr/local/bin/python'
    export DISTRO='OPENBSD'
    export HTTPD_SERVERROOT='/var/www'

    export IRA_HTTPD_USER='www'
    export IRA_HTTPD_GROUP='www'
    export CRON_SPOOL_DIR='/var/cron/tabs'
else
    echo "Cannot detect Linux/BSD distribution. Exit."
    echo "Please contact author iRedMail team <support@iredmail.org> to solve it."
    exit 255
fi

export CRON_FILE_ROOT="${CRON_SPOOL_DIR}/${SYS_ROOT_USER}"

# Optional argument to set the directory which stores iRedAdmin.
if [ $# -gt 0 ]; then
    if [ -d ${1} ]; then
        export HTTPD_SERVERROOT="${1}"
    fi

    if echo ${HTTPD_SERVERROOT} | grep '/iredadmin/*$' > /dev/null; then
        export HTTPD_SERVERROOT="$(dirname ${HTTPD_SERVERROOT})"
    fi
fi

# Dependent package names
# SimpleJson
export DEP_PY_JSON='simplejson'
# BeautifulSoup 4.x
export DEP_PY_BS4='python-beautifulsoup4'
# BeautifulSoup 3.x
export DEP_PY_BS='python-beautifulsoup'
# dnspython
export DEP_PY_DNS='python-dns'
# lxml
export DEP_PY_LXML='python-lxml'
# pycurl
export DEP_PY_CURL='python-pycurl'
if [ X"${DISTRO}" == X'RHEL' ]; then
    :
elif [ X"${DISTRO}" == X'DEBIAN' -o X"${DISTRO}" == X'UBUNTU' ]; then
    export DEP_PY_JSON='python-simplejson'
    export DEP_PY_BS4='python-beautifulsoup'
    export DEP_PY_DNS='python-dnspython'
elif [ X"${DISTRO}" == X'OPENBSD' ]; then
    export DEP_PY_JSON='py-simplejson'
    export DEP_PY_BS4='py-beautifulsoup4'
    export DEP_PY_BS='py-beautifulsoup4'
    export DEP_PY_CURL='py-curl'
    export DEP_PY_DNS='py-dnspython'
elif [ X"${DISTRO}" == X'FREEBSD' ]; then
    export DEP_PY_JSON='devel/py-simplejson'
    export DEP_PY_BS4='www/py-beautifulsoup'
    export DEP_PY_BS='www/py-beautifulsoup32'
    export DEP_PY_LXML='devel/py-lxml'
    export DEP_PY_CURL='ftp/py-pycurl'
    export DEP_PY_DNS='dns/py-dnspython'
fi

# iRedAdmin directory and config file.
export IRA_ROOT_DIR="${HTTPD_SERVERROOT}/iredadmin"
export IRA_CONF_PY="${IRA_ROOT_DIR}/settings.py"
export IRA_CONF_INI="${IRA_ROOT_DIR}/settings.ini"

echo "* Detected Linux/BSD distribution: ${DISTRO}"
echo "* HTTP server root: ${HTTPD_SERVERROOT}"

restart_web_service()
{
    export web_service="${HTTPD_RC_SCRIPT_NAME}"
    if [ -f ${NGINX_PID_FILE} ]; then
        if [ -n "$(cat ${NGINX_PID_FILE})" ]; then
            export web_service="${UWSGI_RC_SCRIPT_NAME}"
        fi
    fi

    echo "* Restarting ${web_service} service to use new iRedAdmin release ..."
    if [ X"${KERNEL_NAME}" == X'LINUX' -o X"${KERNEL_NAME}" == X'FREEBSD' ]; then
        # The uwsgi script on CentOS 6 has problem with 'restart'
        # action, 'stop' with few seconds sleep fixes it.
        if [ X"${DISTRO}" == X'RHEL' -a X"${web_service}" == X'uwsgi' ]; then
            service ${web_service} stop
            sleep 5
            service ${web_service} start
        else
            service ${web_service} restart
        fi
    elif [ X"${KERNEL_NAME}" == X'OPENBSD' ]; then
        rcctl restart ${web_service}
    fi

    if [ X"$?" != X'0' ]; then
        echo "Failed, please restart service ${HTTPD_RC_SCRIPT_NAME} or ${UWSGI_RC_SCRIPT_NAME} (if you're running Nginx as web server) manually."
    fi
}

install_pkg()
{
    echo "Install package: $@"

    if [ X"${DISTRO}" == X'RHEL' ]; then
        yum -y install $@
    elif [ X"${DISTRO}" == X'DEBIAN' -o X"${DISTRO}" == X'UBUNTU' ]; then
        apt-get install -y --force-yes $@
    elif [ X"${DISTRO}" == X'FREEBSD' ]; then
        cd /usr/ports/$@ && make install clean
    elif [ X"${DISTRO}" == X'OPENBSD' ]; then
        pkg_add -r $@
    else
        echo "<< ERROR >> Please install package(s) manually: $@"
    fi
}

add_missing_parameter()
{
    # Usage: add_missing_parameter VARIABLE DEFAULT_VALUE [COMMENT]
    var="${1}"
    value="${2}"
    shift 2
    comment="$@"

    if ! grep "^${var}" ${IRA_CONF_PY} &>/dev/null; then
        if [ ! -z "${comment}" ]; then
            echo "# ${comment}" >> ${IRA_CONF_PY}
        fi

        if [ X"${value}" == X'True' -o X"${value}" == X'False' ]; then
            echo "${var} = ${value}" >> ${IRA_CONF_PY}
        else
            # Value must be quoted as string.
            echo "${var} = '${value}'" >> ${IRA_CONF_PY}
        fi
    fi
}

has_python_module()
{
    mod="$1"
    python -c "import $mod" &>/dev/null
    if [ X"$?" == X'0' ]; then
        echo 'YES'
    else
        echo 'NO'
    fi
}

# Remove all single quote and double quotes in string.
strip_quotes()
{
    # Read input from stdin
    str="$(cat <&0)"
    value="$(echo ${str} | tr -d '"' | tr -d "'")"
    echo "${value}"
}

get_iredadmin_setting()
{
    var="${1}"
    value="$(grep "^${var}" ${IRA_CONF_PY} | awk '{print $NF}' | strip_quotes)"
    echo "${value}"
}

if [ -L ${IRA_ROOT_DIR} ]; then
    export IRA_ROOT_REAL_DIR="$(readlink ${IRA_ROOT_DIR})"
    echo "* Found iRedAdmin directory: ${IRA_ROOT_DIR}, symbol link of ${IRA_ROOT_REAL_DIR}"
else
    echo "<<< ERROR >>> Directory is not a symbol link created by iRedMail. Exit."
    exit 255
fi

# Copy config file
if [ -f ${IRA_CONF_PY} ]; then
    echo "* Found iRedAdmin config file: ${IRA_CONF_PY}"
elif [ -f ${IRA_CONF_INI} ]; then
    echo "* Found iRedAdmin config file: ${IRA_CONF_INI}"
    echo "* Convert config file to new file name and format (settings.py)"
    cp ${IRA_CONF_INI} .
    bash convert_ini_to_py.sh settings.ini && \
        rm -f settings.ini && \
        mv settings.py ${IRA_CONF_PY} && \
        chmod 0400 ${IRA_CONF_PY}
else
    echo "<<< ERROR >>> Cannot find a valid config file (settings.py or settings.ini)."
    exit 255
fi

# Check whether current directory is iRedAdmin
PWD="$(pwd)"
if ! echo ${PWD} | grep 'iRedAdmin-.*/tools' >/dev/null; then
    echo "<<< ERROR >>> Cannot find new version of iRedAdmin in current directory. Exit."
    exit 255
fi

# Copy current directory to Apache server root
dir_new_version="$(dirname ${PWD})"
name_new_version="$(basename ${dir_new_version})"
NEW_IRA_ROOT_DIR="${HTTPD_SERVERROOT}/${name_new_version}"
if [ -d ${NEW_IRA_ROOT_DIR} ]; then
    COPY_FILES="${dir_new_version}/*"
    COPY_DEST_DIR="${NEW_IRA_ROOT_DIR}"
    #echo "<<< ERROR >>> Directory exist: ${NEW_IRA_ROOT_DIR}. Exit."
    #exit 255
else
    COPY_FILES="${dir_new_version}"
    COPY_DEST_DIR="${HTTPD_SERVERROOT}"
fi

echo "* Copying new version to ${NEW_IRA_ROOT_DIR}"
cp -rf ${COPY_FILES} ${COPY_DEST_DIR}

# Copy old config file
cp -p ${IRA_CONF_PY} ${NEW_IRA_ROOT_DIR}/

# Copy hooks.py. It's ok if missing.
cp -p ${IRA_ROOT_DIR}/hooks.py ${NEW_IRA_ROOT_DIR}/ &>/dev/null

# Copy custom files under 'tools/'. It's ok if missing.
cp -p ${IRA_ROOT_DIR}/tools/*.custom ${NEW_IRA_ROOT_DIR}/tools/ &>/dev/null
cp -p ${IRA_ROOT_DIR}/tools/*.last-time ${NEW_IRA_ROOT_DIR}/tools/ &>/dev/null

# Template file renamed
if [ -f "${IRA_ROOT_DIR}/tools/notify_quarantined_recipients.custom.html" ]; then
    cp -f ${IRA_ROOT_DIR}/tools/notify_quarantined_recipients.custom.html \
        ${NEW_IRA_ROOT_DIR}/tools/notify_quarantined_recipients.html.custom
fi

# Set owner and permission.
chown -R ${IRA_HTTPD_USER}:${IRA_HTTPD_GROUP} ${NEW_IRA_ROOT_DIR}
chmod -R 0555 ${NEW_IRA_ROOT_DIR}
chmod 0400 ${NEW_IRA_ROOT_DIR}/settings.py

echo "* Removing old symbol link ${IRA_ROOT_DIR}"
rm -f ${IRA_ROOT_DIR}

echo "* Creating symbol link ${IRA_ROOT_DIR} to ${NEW_IRA_ROOT_DIR}"
cd ${HTTPD_SERVERROOT}
ln -s ${name_new_version} iredadmin

# Delete all sessions to force admins to re-login.
cd ${NEW_IRA_ROOT_DIR}/tools/
python delete_sessions.py

# Add missing setting parameters.
if grep 'amavisd_enable_logging.*True.*' ${IRA_CONF_PY} &>/dev/null; then
    add_missing_parameter 'amavisd_enable_policy_lookup' True 'Enable per-recipient spam policy, white/blacklist.'
else
    add_missing_parameter 'amavisd_enable_policy_lookup' False 'Enable per-recipient spam policy, white/blacklist.'
fi

if ! grep '^iredapd_' ${IRA_CONF_PY} &>/dev/null; then
    add_missing_parameter 'iredapd_enabled' True 'Enable iRedAPD integration.'

    # Get iredapd db password from /opt/iredapd/settings.py.
    if [ -f /opt/iredapd/settings.py ]; then
        grep '^iredapd_db_' /opt/iredapd/settings.py >> ${IRA_CONF_PY}
        perl -pi -e 's#iredapd_db_server#iredapd_db_host#g' ${IRA_CONF_PY}
    else
        # Check backend.
        if egrep '^backend.*pgsql' ${IRA_CONF_PY} &>/dev/null; then
            export IREDAPD_DB_PORT='5432'
        else
            export IREDAPD_DB_PORT='3306'
        fi

        add_missing_parameter 'iredapd_db_host' '127.0.0.1'
        add_missing_parameter 'iredapd_db_port' ${IREDAPD_DB_PORT}
        add_missing_parameter 'iredapd_db_name' 'iredapd'
        add_missing_parameter 'iredapd_db_user' 'iredapd'
        add_missing_parameter 'iredapd_db_password' 'password'
    fi
fi
perl -pi -e 's#iredapd_db_server#iredapd_db_host#g' ${IRA_CONF_PY}

# Change old parameter names to the new ones:
#
#   - ADDITION_USER_SERVICES -> ADDITIONAL_ENABLED_USER_SERVICES
#   - LDAP_SERVER_NAME -> LDAP_SERVER_PRODUCT_NAME
perl -pi -e 's#ADDITION_USER_SERVICES#ADDITIONAL_ENABLED_USER_SERVICES#g' ${IRA_CONF_PY}
perl -pi -e 's#LDAP_SERVER_NAME#LDAP_SERVER_PRODUCT_NAME#g' ${IRA_CONF_PY}

# Remove deprecated setting: ENABLE_SELF_SERVICE, it's now a per-domain setting.
perl -pi -e 's#^(ENABLE_SELF_SERVICE.*)##g' ${IRA_CONF_PY}

# Check dependent packages. Prompt to install missed ones manually.
echo "* Check and install dependent Python modules:"
echo "  + [required] json or simplejson"
if [ X"$(has_python_module json)" == X'NO' \
     -a X"$(has_python_module simplejson)" == X'NO' ]; then
    install_pkg $DEP_PY_JSON
fi

echo "  + [required] dnspython"
[ X"$(has_python_module dns)" == X'NO' ] && install_pkg $DEP_PY_DNS

echo "  + [required] pycurl"
[ X"$(has_python_module pycurl)" == X'NO' ] && install_pkg $DEP_PY_CURL

echo "  + [optional] BeautifulSoup"
if [ X"$(has_python_module bs4)" == X'NO' \
     -a X"$(has_python_module BeautifulSoup)" == X'NO' ]; then
    install_pkg $DEP_PY_BS4
fi

echo "  + [optional] lxml"
[ X"$(has_python_module lxml)" == X'NO' ] && install_pkg $DEP_PY_LXML


#------------------------------------------
# Add new SQL tables, drop deprecated ones.
#
export ira_db_host="$(get_iredadmin_setting 'iredadmin_db_host')"
export ira_db_port="$(get_iredadmin_setting 'iredadmin_db_port')"
export ira_db_name="$(get_iredadmin_setting 'iredadmin_db_name')"
export ira_db_user="$(get_iredadmin_setting 'iredadmin_db_user')"
export ira_db_password="$(get_iredadmin_setting 'iredadmin_db_password')"

#
# Update sql tables
#
mysql_conn="mysql -h${ira_db_host} \
                  -P${ira_db_port} \
                  -u${ira_db_user} \
                  -p${ira_db_password} \
                  ${ira_db_name}"

psql_conn="psql -h ${ira_db_host} \
                -p ${ira_db_port} \
                -U ${ira_db_user} \
                -d ${ira_db_name}"

if egrep '^backend.*(mysql|ldap)' ${IRA_CONF_PY} &>/dev/null; then
    echo "* Check SQL tables, and add missed ones - if there's any"
    ${mysql_conn} -e "SOURCE ${IRA_ROOT_DIR}/SQL/iredadmin.mysql"

elif egrep '^backend.*pgsql' ${IRA_CONF_PY} &>/dev/null; then
    export PGPASSWORD="${ira_db_password}"

    # SQL table: tracking.
    ${psql_conn} -c '\d' | grep '\<tracking\>' &>/dev/null
    if [ X"$?" != X'0' ]; then
        echo "* [SQL] Add new table: iredadmin.tracking."

        ${psql_conn} <<EOF
CREATE TABLE tracking (
    k VARCHAR(50) NOT NULL,
    v TEXT,
    time TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_tracking_k ON tracking (k);
EOF
    fi

    # SQL table: domain_ownership.
    ${psql_conn} -c '\d' | grep '\<domain_ownership\>' &>/dev/null
    if [ X"$?" != X'0' ]; then
        echo "* [SQL] Add new table: iredadmin.domain_ownership."

        ${psql_conn} <<EOF
CREATE TABLE domain_ownership (
    id SERIAL PRIMARY KEY,
    admin VARCHAR(255) NOT NULL DEFAULT '',
    domain VARCHAR(255) NOT NULL DEFAULT '',
    alias_domain VARCHAR(255) NOT NULL DEFAULT '',
    verify_code VARCHAR(100) NOT NULL DEFAULT '',
    verified INT2 NOT NULL DEFAULT 0,
    message TEXT,
    last_verify TIMESTAMP NULL DEFAULT NULL,
    expire INT DEFAULT 0
);
CREATE UNIQUE INDEX idx_ownership_1 ON domain_ownership (admin, domain, alias_domain);
CREATE INDEX idx_ownership_2 ON domain_ownership (verified);
EOF
    fi
fi

#------------------------------
# Cron job.
#
[[ -d ${CRON_SPOOL_DIR} ]] || mkdir -p ${CRON_SPOOL_DIR} &>/dev/null
if [[ ! -f ${CRON_FILE_ROOT} ]]; then
    touch ${CRON_FILE_ROOT} &>/dev/null
    chmod 0600 ${CRON_FILE_ROOT} &>/dev/null
fi

# cron job: clean up database.
if ! grep 'iredadmin/tools/cleanup_db.py' ${CRON_FILE_ROOT} &>/dev/null; then
    cat >> ${CRON_FILE_ROOT} <<EOF
# iRedAdmin: Clean up sql database.
1   *   *   *   *   ${PYTHON_BIN} ${IRA_ROOT_DIR}/tools/cleanup_db.py &>/dev/null
EOF
fi

# cron job: clean up database.
if ! grep 'iredadmin/tools/delete_mailboxes.py' ${CRON_FILE_ROOT} &>/dev/null; then
    cat >> ${CRON_FILE_ROOT} <<EOF
# iRedAdmin: Remove mailboxes which are scheduled to be removed.
1   3   *   *   *   ${PYTHON_BIN} ${IRA_ROOT_DIR}/tools/delete_mailboxes.py
EOF
fi


echo "* iRedAdmin has been successfully upgraded."
restart_web_service

# Clean up.
cd ${NEW_IRA_ROOT_DIR}/
rm -f settings.pyc settings.pyo tools/settings.py

echo "* Upgrading completed."

cat <<EOF
<<< NOTE >>> If iRedAdmin doesn't work as expected, please post your issue in
<<< NOTE >>> our online support forum: http://www.iredmail.org/forum/
EOF
