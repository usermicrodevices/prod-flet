import flet as ft
from log_tools import *
from translation import _


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


class AboutDialog(ft.AlertDialog):
    def __init__(self, *args, **kwargs):
        page = kwargs.pop('page')
        super().__init__(*args, **kwargs)
        CONTENT = f'''{_("Version")} {VERSION}\n''' + \
            f'''Esc - {_("close any dialog")}\n''' + \
            f'''F1 - {_("this dialog")}\n''' + \
            f'''F2 - {_("select customer")}\n''' + \
            f'''Ctrl+F2 - {_("reset customer")}\n''' + \
            f'''F3 - {_("switch between search and final sum")}\n''' + \
            f'''F4 - {_("switch between search and count last product")}\n''' + \
            f'''F5 - {_("switch between search and scanning")}\n''' + \
            f'''F10 - {_("finish order provider")}\n''' + \
            f'''F11 - {_("finish order customer")}\n''' + \
            f'''F12 - {_("finish sale")}\n''' + \
            f'''(flet {_("version")} {ft.version.version})'''

        self.content = ft.Text(CONTENT)
        self.actions = [ft.TextButton('close', on_click=lambda evt: page.close(evt.control.parent))]
