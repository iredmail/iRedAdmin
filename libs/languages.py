# encoding: utf-8
# Author: Zhang Huangbin <zhb@iredmail.org>

import os
import glob
import web

langmaps = {
    'en_US': u'English (US)',
    'sq_AL': u'Albanian',
    'ar_SA': u'Arabic',
    'hy_AM': u'Armenian',
    'az_AZ': u'Azerbaijani',
    'bs_BA': u'Bosnian (Serbian Latin)',
    'bg_BG': u'Bulgarian',
    'ca_ES': u'Català',
    'cy_GB': u'Cymraeg',
    'hr_HR': u'Croatian (Hrvatski)',
    'cs_CZ': u'Čeština',
    'da_DK': u'Dansk',
    'de_DE': u'Deutsch (Deutsch)',
    'de_CH': u'Deutsch (Schweiz)',
    'en_GB': u'English (GB)',
    'es_ES': u'Español',
    'eo': u'Esperanto',
    'et_EE': u'Estonian',
    'eu_ES': u'Euskara (Basque)',
    'fi_FI': u'Finnish (Suomi)',
    'nl_BE': u'Flemish',
    'fr_FR': u'Français',
    'gl_ES': u'Galego (Galician)',
    'ka_GE': u'Georgian (Kartuli)',
    'el_GR': u'Greek',
    'he_IL': u'Hebrew',
    'hi_IN': u'Hindi',
    'hu_HU': u'Hungarian',
    'is_IS': u'Icelandic',
    'id_ID': u'Indonesian',
    'ga_IE': u'Irish',
    'it_IT': u'Italiano',
    'ja_JP': u'Japanese (日本語)',
    'ko_KR': u'Korean',
    'ku': u'Kurdish (Kurmancî)',
    'lv_LV': u'Latvian',
    'lt_LT': u'Lithuanian',
    'mk_MK': u'Macedonian',
    'ms_MY': u'Malay',
    'nl_NL': u'Netherlands',
    'ne_NP': u'Nepali',
    'nb_NO': u'Norsk (Bokmål)',
    'nn_NO': u'Norsk (Nynorsk)',
    'fa': u'Persian (Farsi)',
    'pl_PL': u'Polski',
    'pt_BR': u'Portuguese (Brazilian)',
    'pt_PT': u'Portuguese (Standard)',
    'ro_RO': u'Romanian',
    'ru_RU': u'Русский',
    'sr_CS': u'Serbian (Cyrillic)',
    'si_LK': u'Sinhala',
    'sk_SK': u'Slovak',
    'sl_SI': u'Slovenian',
    'sv_SE': u'Swedish (Svenska)',
    'th_TH': u'Thai',
    'tr_TR': u'Türkçe',
    'uk_UA': u'Ukrainian',
    'vi_VN': u'Vietnamese',
    'zh_CN': u'简体中文',
    'zh_TW': u'繁體中文',
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
