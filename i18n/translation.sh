#!/bin/sh

# =========================================================
# Author:    Zhang Huangbin (michaelbibby@gmail.com)
# =========================================================

ACTION="$1"

DOMAIN="iredadmin"
POFILE="${DOMAIN}.po"
AVAILABLE_LANGS="$(ls -d *_*)"

if [ X"${ACTION}" == X"extract" ]; then
    # Extract.
    echo "* Extract localizable messages from template files to ${POFILE}..."
    pybabel -v extract -F babel.cfg \
        --charset=utf-8 \
        --sort-by-file \
        --msgid-bugs-address=michaelbibby@gmail.com \
        -o ${POFILE} \
        .. >/dev/null

elif [ X"${ACTION}" == X"update" ]; then
    # Update.
    echo "* Update existing new translations catalog based on ${POFILE}..."
    for lang in ${AVAILABLE_LANGS}
    do
        pybabel update -i ${POFILE} \
            -D ${DOMAIN} \
            -d . \
            -l ${lang}
    done

elif [ X"${ACTION}" == X"compile" ]; then
    echo "* Compile translation catalogs into binary MO files..."
    for lang in ${AVAILABLE_LANGS}
    do
        pybabel compile -f -i ${POFILE} \
            -D ${DOMAIN} \
            -d . \
            -l ${lang}
    done
elif [ X"${ACTION}" == X"all" ]; then
    bash $0 extract && \
    bash $0 update && \
    bash $0 compile
else
    :
fi
