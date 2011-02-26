#!/usr/bin/env bash

# =========================================================
# Author:    Zhang Huangbin (michaelbibby@gmail.com)
# =========================================================

#---------------------------------------------------------------------
# This file is part of iRedAdmin-Pro, which is official web-based admin
# panel (Full-Featured Edition) for iRedMail.
#
# ---- Restrictions ----
# * Source code is only available after you purchase it, so that you can
#   modify it to fit your need, but it is NOT allowed to redistribute
#   and sell iRedAdmin and the one you modified based on iRedAdmin.
#
# * We will do our best to solve all bugs found in official iRedAdmin,
#   but we are not guarantee to solve bugs occured in your modified copy.
#
# * It is NOT allowed to deployed on more than 1 server.
#
#---------------------------------------------------------------------

# Available actions: [all, LANG].
ACTIONORLANG="$1"

if [ -z "${ACTIONORLANG}" ]; then
    cat <<EOF

Usage: $0 [all, LANGUAGE]

Example:

    $ $0 all
    $ $0 zh_CN
    $ $0 fr_Fr

EOF
    exit 255
fi

DOMAIN="iredadmin"
POFILE="${DOMAIN}.po"
AVAILABLE_LANGS="$(ls -d *_*)"

extractLastest()
{
    # Extract strings from template files.
    echo "* Extract localizable messages from template files to ${POFILE}..."

        #--no-location \
    pybabel -v extract -F babel.cfg \
        --sort-output \
        --charset=utf-8 \
        --msgid-bugs-address=zhb@iredmail.org \
        -o ${POFILE} \
        .. >/dev/null
}

updatePO()
{
    # Update PO files.
    echo "* Update existing new translations catalog based on ${POFILE}..."

    # Get iRedAdmin version number.
    export version=$(grep '^__version__' ../libs/__init__.py | awk -F"'" '{print $2}')

    for lang in ${LANGUAGES}
    do
        [ -d ${lang}/LC_MESSAGES/ ] || mkdir -p ${lang}/LC_MESSAGES/
        pybabel update -i ${POFILE} \
            -D ${DOMAIN} \
            -d . \
            -l ${lang}

        # Add project name and version number.
        perl -pi -e 's#(.*Project-Id-Version:).*#${1} iRedAdmin-Pro-$ENV{version}\\n"#' ${lang}/LC_MESSAGES/${DOMAIN}.po

        # Remove 'fuzzy' tag.
        perl -pi -e 's/#, fuzzy//' ${lang}/LC_MESSAGES/${DOMAIN}.po
    done
}

convertPO2MO()
{
    echo "* Convert translation catalogs into binary MO files..."
    for lang in ${LANGUAGES}
    do
        echo "  + Converting ${lang}..."
        msgfmt --statistics -c ${lang}/LC_MESSAGES/${DOMAIN}.po -o ${lang}/LC_MESSAGES/${DOMAIN}.mo
    done
}

if [ X"${ACTIONORLANG}" == X"all" -o X"${ACTIONORLANG}" == X"" ]; then
    export LANGUAGES="${AVAILABLE_LANGS}"
else
    export LANGUAGES="${ACTIONORLANG}"
fi

extractLastest && \
updatePO && \
convertPO2MO
