import gettext, locale, logging, os, re

global gettext_catalog
gettext_catalog = None

def set_locale(current_locale=None, encoding=None, locale_dir='locale'):
    global gettext_catalog
    if not os.path.isdir(locale_dir):
        os.mkdir(locale_dir)
    if encoding is None:
        encoding = locale.getencoding()
    if current_locale is None:
        current_locale = locale.getlocale()
    if isinstance(current_locale, (list, tuple)):
        current_locale, encoding = current_locale
    else:
        res = re.match(r"\('(\S+)', '(\S+)'\)", current_locale) or re.match(r"\['(\S+)', '(\S+)'\]", current_locale)
        if res:
            grps = res.groups()
            if len(grps) == 2:
                current_locale, encoding = grps
    new_locale = f'{current_locale}.{encoding}' if current_locale else ''
    try:
        locale.setlocale(locale.LC_ALL, new_locale)
        locale.setlocale(locale.LC_CTYPE, new_locale)
    except Exception as e:
        logging.error(['🆘', __name__, new_locale, e, f'🇱🇮🇳🇪{e.__traceback__.tb_lineno}'])
        return False
    else:
        lang = gettext.translation('prod', locale_dir, languages=[current_locale])
        lang.install()
        if current_locale:
            os.environ['LANGUAGE'] = f'{current_locale}:{current_locale[:2]}'
        if new_locale:
            os.environ['LANG'] = new_locale
            os.environ['LC_ALL'] = new_locale
            os.environ['LC_CTYPE'] = new_locale
        logging.debug(['⛳㊗APPLICATION LANGUAGE㊗⛳', current_locale, encoding, '🖼DIRECTORY🖼', locale_dir])
    gettext_catalog = gettext.Catalog('prod', locale_dir)
    return True

def _(value):
    global gettext_catalog
    if gettext_catalog:
        return gettext_catalog.gettext(value)
    return value
