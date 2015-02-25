#!/usr/bin/env bash

# Purpose: Upgrade iRedAdmin from old release.
#          Works with both iRedAdmin open souce edition or iRedAdmin-Pro.

# USAGE:
#
#   # cd /path/to/iRedAdmin-xxx/tools/
#   # bash upgrade_iredadmin.sh

export IRA_HTTPD_USER='iredadmin'
export IRA_HTTPD_GROUP='iredadmin'

# Check OS to detect some necessary info.
export KERNEL_NAME="$(uname -s | tr '[a-z]' '[A-Z]')"
export UWSGI_RC_SCRIPT_NAME='uwsgi'
export NGINX_PID_FILE='/var/run/nginx.pid'

if [ X"${KERNEL_NAME}" == X"LINUX" ]; then
    if [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        export DISTRO='RHEL'
        export HTTPD_SERVERROOT='/var/www'
        export HTTPD_RC_SCRIPT_NAME='httpd'
    elif [ -f /etc/lsb-release ]; then
        # Ubuntu
        export DISTRO='UBUNTU'
        export HTTPD_SERVERROOT='/usr/share/apache2'
        export HTTPD_RC_SCRIPT_NAME='apache2'
    elif [ -f /etc/debian_version ]; then
        # Debian
        export DISTRO='DEBIAN'
        export HTTPD_SERVERROOT='/usr/share/apache2'
        export HTTPD_RC_SCRIPT_NAME='apache2'
    elif [ -f /etc/SuSE-release ]; then
        # openSUSE
        export DISTRO='SUSE'
        export HTTPD_SERVERROOT='/srv/www'
        export HTTPD_RC_SCRIPT_NAME='apache2'
    else
        echo "<<< ERROR >>> Cannot detect Linux distribution name. Exit."
        echo "Please contact support@iredmail.org to solve it."
        exit 255
    fi
elif [ X"${KERNEL_NAME}" == X'FREEBSD' ]; then
    export DISTRO='FREEBSD'
    export HTTPD_SERVERROOT='/usr/local/www'
    if [ -f /usr/local/etc/rc.d/apache24 ]; then
        export HTTPD_RC_SCRIPT_NAME='apache24'
    else:
        export HTTPD_RC_SCRIPT_NAME='apache22'
    fi
elif [ X"${KERNEL_NAME}" == X'OPENBSD' ]; then
    export DISTRO='OPENBSD'
    export HTTPD_SERVERROOT='/var/www'

    export IRA_HTTPD_USER='www'
    export IRA_HTTPD_GROUP='www'
else
    echo "Cannot detect Linux/BSD distribution. Exit."
    echo "Please contact author iRedMail team <support@iredmail.org> to solve it."
    exit 255
fi

# Optional argument to set the directory which stores iRedAdmin.
if [ $# -gt 0 ]; then
    if [ -d ${1} ]; then
        export HTTPD_SERVERROOT="${1}"
    fi

    if echo ${HTTPD_SERVERROOT} | grep '/iredadmin/*$' > /dev/null; then
        export HTTPD_SERVERROOT="$(dirname ${HTTPD_SERVERROOT})"
    fi
fi

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

    echo -n "* Restart service (${web_service}) to use new iRedAdmin release now? [Y|n] "
    read answer
    case $answer in
        y|Y|yes|YES )
            if [ X"${KERNEL_NAME}" == X'LINUX' ]; then
                service ${web_service} restart
            elif [ X"${KERNEL_NAME}" == X'FREEBSD' ]; then
                /usr/local/etc/rc.d/${web_service} restart
            elif [ X"${KERNEL_NAME}" == X'OPENBSD' ]; then
                /etc/rc.d/${web_service} restart
            fi

            if [ X"$?" != X'0' ]; then
                echo "Failed, please restart service ${HTTPD_RC_SCRIPT_NAME} or ${UWSGI_RC_SCRIPT_NAME} (if you're running Nginx as web server) manually."
            fi
            ;;
        n|N|no|NO|* ) echo "* SKIPPED, please restart service ${HTTPD_RC_SCRIPT_NAME} or ${UWSGI_RC_SCRIPT_NAME} (if you're running Nginx as web server) manually."
    esac
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

# iRedAdmin directory and config file.
export IRA_ROOT_DIR="${HTTPD_SERVERROOT}/iredadmin"
export IRA_CONF_PY="${IRA_ROOT_DIR}/settings.py"
export IRA_CONF_INI="${IRA_ROOT_DIR}/settings.ini"

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

# Check whether it's iRedAdmin-Pro
IS_IRA_PRO='NO'
if echo ${PWD} | grep 'iRedAdmin-Pro-.*/tools' >/dev/null; then
    IS_IRA_PRO='YES'
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
cp -p ${IRA_CONF_PY} ${NEW_IRA_ROOT_DIR}/
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

# Sync virtual mail domains to Cluebringer policy group '@internal_domains'.
if grep 'policyd_db_name.*cluebringer.*' ${IRA_CONF_PY} &>/dev/null; then
    echo "* Add existing virtual mail domains to Cluebringer database as internal domains."

    python sync_cluebringer_internal_domains.py
fi

# Add missing setting parameters.
if grep 'amavisd_enable_logging.*True.*' ${IRA_CONF_PY} &>/dev/null; then
    add_missing_parameter 'amavisd_enable_policy_lookup' True 'Enable per-recipient spam policy, white/blacklist.'
else
    add_missing_parameter 'amavisd_enable_policy_lookup' False 'Enable per-recipient spam policy, white/blacklist.'
fi

if [ X"${IS_IRA_PRO}" == X'YES' ]; then
    # Enable self-service
    cat <<EOF
* Would you like to enable self-service? With self-service, mail users can login to"
  iRedAdmin-Pro to manage their own preferences, including mail forwarding, changing"
  password, manage per-user white/blacklists and spam policy. You can control allowed"
  preferences in domain profile page."
EOF

    echo -n "  Enable self-service now? [y|N] "

    read answer
    case $answer in
        y|Y|yes|YES )
            if ! grep '^ENABLE_SELF_SERVICE' ${IRA_CONF_PY} &>/dev/null; then
                echo "* Add new setting 'ENABLE_SELF_SERVICE = True' in config file ${IRA_CONF_PY}."
                echo 'ENABLE_SELF_SERVICE = True' >> ${IRA_CONF_PY}
            elif grep '^ENABLE_SELF_SERVICE' ${IRA_CONF_PY} &>/dev/null; then
                echo "* Update setting 'ENABLE_SELF_SERVICE' to True in config file ${IRA_CONF_PY}."
                perl -pi -e 's#^(ENABLE_SELF_SERVICE).*#${1} = True#g' ${IRA_CONF_PY}
            fi
            ;;
        n|N|no|NO|* ) echo "* SKIPPED, didn't touch iRedAdmin config file." ;;
    esac
fi

echo "* iRedAdmin was successfully upgraded, restarting web service is required."
restart_web_service

# Clean up.
cd ${NEW_IRA_ROOT_DIR}/
rm -f settings.pyc settings.pyo tools/settings.py

echo "* Upgrading completed."

cat <<EOF
<<< NOTE >>> If iRedAdmin doesn't work as expected, please post your issue in
<<< NOTE >>> our online support forum: http://www.iredmail.org/forum/
EOF
