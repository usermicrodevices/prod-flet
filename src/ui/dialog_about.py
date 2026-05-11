import flet
from log_tools import *
from translation import _

global VERSION
VERSION = ''
try:
    import tomllib
except Exception as e:
    logging.error(['IMPORT TOMLLIB', e])
else:
    try:
        f = open("pyproject.toml", "rb")
    except Exception as e:
        logging.error(['OPEN PYPROJECT.TOML', e])
    else:
            data = tomllib.load(f)
            VERSION = data['project']['version']


class AboutDialog(flet.AlertDialog):
    def __init__(self, *args, **kwargs):
        global VERSION
        #page = kwargs.pop('page')
        super().__init__(*args, **kwargs)
        if not VERSION:
            VERSION = 'UNKNOWN'
        CONTENT = f'''{_("Version")} {VERSION}\n''' + \
            f'''Esc - {_("close any dialog")}\n''' + \
            f'''F1 - {_("this dialog")}\n''' + \
            f'''F2 - {_("select customer")}\n''' + \
            f'''Ctrl+F2 - {_("reset customer")}\n''' + \
            f'''F3 - {_("switch between search and final sum")}\n''' + \
            f'''F4 - {_("switch between search and count last product")}\n''' + \
            f'''F5 - {_("switch between search and scanning")}\n''' + \
            f'''F6 - {_("settings")}\n''' + \
            f'''F9 - {_("open navigation menu")}\n''' + \
            f'''F10 - {_("finish order provider")}\n''' + \
            f'''F11 - {_("finish order customer")}\n''' + \
            f'''F12 - {_("finish sale")}\n''' + \
            f'''Ctrl+DEL - {_("clear products from basket")}\n''' + \
            f'''(Flet {_("version")} {flet.__version__})\n''' + \
            f'''(Flutter {_("version")} {flet.version.flutter_version})'''

        self.content = flet.Text(CONTENT)
        self.actions = [flet.TextButton('close', on_click=lambda evt: self.page.pop_dialog())]#evt.control.parent
