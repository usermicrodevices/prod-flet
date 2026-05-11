import gettext, locale, logging, os, re

global gettext_catalog
gettext_catalog = None

pattern = re.compile(r"""^\s*([\(\[])\s*['"]?(\S+?)['"]?\s*,\s*['"]?(\S+?)['"]?\s*([\)\]])\s*$""", re.VERBOSE)

def match_pair(s):
    m = pattern.match(s)
    if not m:
        return None
    open_b, v1, v2, close_b = m.group(1), m.group(2), m.group(3), m.group(4)
    if (open_b == '(' and close_b == ')') or (open_b == '[' and close_b == ']'):
        return v1, v2
    return None

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
        current_locale, encoding = match_pair(current_locale)
    new_locale = f'{current_locale}.{encoding}' if current_locale else ''
    try:
        locale.setlocale(locale.LC_ALL, new_locale)
        locale.setlocale(locale.LC_CTYPE, new_locale)
    except Exception as err:
        logging.error(['🆘', f'{__name__}.py', new_locale, err, f'🇱🇮🇳🇪{err.__traceback__.tb_lineno}'])
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
