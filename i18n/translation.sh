#!/usr/bin/env bash

# =========================================================
# Author:    Zhang Huangbin (michaelbibby@gmail.com)
# =========================================================

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
    pybabel -v extract -F babel.cfg \
        --charset=utf-8 \
        --sort-by-file \
        --msgid-bugs-address=michaelbibby@gmail.com \
        -o ${POFILE} \
        .. >/dev/null
}

updatePO()
{
    # Update PO files.
    echo "* Update existing new translations catalog based on ${POFILE}..."

    # Get iRedAdmin version number.
    export version=$(grep '__version__' ../libs/__init__.py | awk -F"'" '{print $2}')

    for lang in ${LANGUAGES}
    do
        [ -d ${lang}/LC_MESSAGES/ ] || mkdir -p ${lang}/LC_MESSAGES/
        pybabel update -i ${POFILE} \
            -D ${DOMAIN} \
            -d . \
            -l ${lang}
        perl -pi -e 's#(.*Project-Id-Version:).*#${1} iRedAdmin $ENV{version}\\n"#' ${lang}/LC_MESSAGES/${DOMAIN}.po
    done
}

convertPO2MO()
{
    echo "* Convert translation catalogs into binary MO files..."
    for lang in ${LANGUAGES}
    do
        echo "  + Converting ${lang}..."
        python ./msgfmt.py ${lang}/LC_MESSAGES/${DOMAIN}.po
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
