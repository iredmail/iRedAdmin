# encoding: utf-8
# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import glob
import web

langmaps = {
    'en_US': 'English (US)',
    'sq_AL': 'Albanian',
    'ar_SA': 'Arabic',
    'hy_AM': 'Armenian',
    'az_AZ': 'Azerbaijani',
    'bs_BA': 'Bosnian (Serbian Latin)',
    'bg_BG': 'Bulgarian',
    'ca_ES': 'Català',
    'cy_GB': 'Cymraeg',
    'hr_HR': 'Croatian (Hrvatski)',
    'cs_CZ': 'Čeština',
    'da_DK': 'Dansk',
    'de_DE': 'Deutsch (Deutsch)',
    'de_CH': 'Deutsch (Schweiz)',
    'en_GB': 'English (GB)',
    'es_ES': 'Español',
    'eo': 'Esperanto',
    'et_EE': 'Estonian',
    'eu_ES': 'Euskara (Basque)',
    'fi_FI': 'Finnish (Suomi)',
    'nl_BE': 'Flemish',
    'fr_FR': 'Français',
    'gl_ES': 'Galego (Galician)',
    'ka_GE': 'Georgian (Kartuli)',
    'el_GR': 'Greek',
    'he_IL': 'Hebrew',
    'hi_IN': 'Hindi',
    'hu_HU': 'Hungarian',
    'is_IS': 'Icelandic',
    'id_ID': 'Indonesian',
    'ga_IE': 'Irish',
    'it_IT': 'Italiano',
    'ja_JP': 'Japanese (日本語)',
    'ko_KR': 'Korean',
    'ku': 'Kurdish (Kurmancî)',
    'lv_LV': 'Latvian',
    'lt_LT': 'Lithuanian',
    'mk_MK': 'Macedonian',
    'ms_MY': 'Malay',
    'nl_NL': 'Netherlands',
    'ne_NP': 'Nepali',
    'nb_NO': 'Norsk (Bokmål)',
    'nn_NO': 'Norsk (Nynorsk)',
    'fa': 'Persian (Farsi)',
    'pl_PL': 'Polski',
    'pt_BR': 'Portuguese (Brazilian)',
    'pt_PT': 'Portuguese (Standard)',
    'ro_RO': 'Romanian',
    'ru_RU': 'Русский',
    'sr_CS': 'Serbian (Cyrillic)',
    'si_LK': 'Sinhala',
    'sk_SK': 'Slovak',
    'sl_SI': 'Slovenian',
    'sv_SE': 'Swedish (Svenska)',
    'th_TH': 'Thai',
    'tr_TR': 'Türkçe',
    'uk_UA': 'Ukrainian',
    'vi_VN': 'Vietnamese',
    'zh_CN': '简体中文',
    'zh_TW': '繁體中文',
}

# All available timezone names and time offsets (in minutes).
allTimezonesOffsets = {
    'GMT-12:00': -720,
    'GMT-11:00': -660,
    'GMT-10:00': -600,
    'GMT-09:30': -570,
    'GMT-09:00': -540,
    'GMT-08:00': -480,
    'GMT-07:00': -420,
    'GMT-06:00': -360,
    'GMT-05:00': -300,
    'GMT-04:30': -270,
    'GMT-04:00': -240,
    'GMT-03:30': -210,
    'GMT-03:00': -180,
    'GMT-02:00': -120,
    'GMT-01:00': -60,
    'GMT': 0,
    'GMT+01:00': 60,
    'GMT+02:00': 120,
    'GMT+03:00': 180,
    'GMT+03:30': 210,
    'GMT+04:00': 240,
    'GMT+04:30': 270,
    'GMT+05:00': 300,
    'GMT+05:30': 330,
    'GMT+05:45': 345,
    'GMT+06:00': 360,
    'GMT+06:30': 390,
    'GMT+07:00': 420,
    'GMT+08:00': 480,
    'GMT+08:45': 525,
    'GMT+09:00': 540,
    'GMT+09:30': 570,
    'GMT+10:00': 600,
    'GMT+10:30': 630,
    'GMT+11:00': 660,
    'GMT+11:30': 690,
    'GMT+12:00': 720,
    'GMT+12:45': 765,
    'GMT+13:00': 780,
    'GMT+14:00': 840,
}


# Get available languages.
def get_language_maps():
    # Get available languages.
    rootdir = os.path.abspath(os.path.dirname(__file__)) + '/../'

    available_langs = [
        web.safestr(os.path.basename(v))
        for v in glob.glob(rootdir + 'i18n/[a-z][a-z]_[A-Z][A-Z]')
        if os.path.basename(v) in langmaps]

    available_langs += [
        web.safestr(os.path.basename(v))
        for v in glob.glob(rootdir + 'i18n/[a-z][a-z]')
        if os.path.basename(v) in langmaps]

    available_langs.sort()

    # Get language maps.
    languagemaps = {}
    for i in available_langs:
        if i in langmaps:
            languagemaps.update({i: langmaps[i]})

    return languagemaps
