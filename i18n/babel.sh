#!/bin/sh

# =========================================================
# Author:    Zhang Huangbin (michaelbibby@gmail.com)
# =========================================================

ACTION="$1"

POFILE="iredadmin.po"

if [ X"${ACTION}" == X"extract" ]; then
    # Extract.
    pybabel -v extract -F babel.cfg \
        --charset=utf-8 \
        --sort-by-file \
        --msgid-bugs-address=michaelbibby@gmail.com \
        -o ${POFILE} \
        ..
elif [ X"${ACTION}" == X"update" ]; then
    # Update.
    pybabel update -i ${POFILE} \
        --ignore-obsolete \
        --previous \
        -D iredadmin \
        -d . \
        -l zh_CN
else
    :
fi
