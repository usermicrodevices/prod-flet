import flet as ft, locale

from log_tools import *
from background_tasks import sync_products
from translation import set_locale


class SettingsDialogAction(ft.CupertinoDialogAction):
    def __init__(self, *args, **kwargs):
        self.is_ok = kwargs.pop('is_ok', False)
        if self.is_ok:
            kwargs['is_destructive_action'] = True
        if 'is_default_action' not in kwargs:
            kwargs['is_default_action'] = False
        super().__init__(*args, **kwargs)


class SettingsDialog(ft.CupertinoAlertDialog):
    def __init__(self, *args, **kwargs):
        page = kwargs.pop('page')
        super().__init__(*args, **kwargs)
        #self.title = ft.TextField('Settings Dialog')
        self.protocol = ft.TextField(hint_text='protocol', label='protocol', expand=True, value=page.client_storage.get('protocol'))
        self.host = ft.TextField(hint_text='host', label='host', expand=True, value=page.client_storage.get('host'))
        self.port = ft.TextField(hint_text='port', label='port', input_filter=ft.NumbersOnlyInputFilter(), keyboard_type=ft.KeyboardType.NUMBER, expand=True, value=page.client_storage.get('port'))
        self.login = ft.TextField(hint_text='login', label='login', expand=True, value=page.client_storage.get('login'))
        self.password = ft.TextField(hint_text='password', label='password', password=True, can_reveal_password=True, expand=True, value=page.client_storage.get('password'))
        self.network_timeout_get_product = ft.TextField(hint_text='0.1', label='timeout get product seconds', input_filter=ft.NumbersOnlyInputFilter(), keyboard_type=ft.KeyboardType.NUMBER, expand=True, value=page.client_storage.get('network_timeout_get_product') or .1)
        self.db_file_name = ft.TextField(hint_text='db file name', label='db file name', expand=True, value=page.client_storage.get('db_file_name') or 'prod.db')
        self.sync_products_interval = ft.TextField(hint_text='seconds', label='sync products interval', input_filter=ft.NumbersOnlyInputFilter(), keyboard_type=ft.KeyboardType.NUMBER, expand=True, value=page.client_storage.get('sync_products_interval') or '7200')
        self.sync_sales_interval = ft.TextField(hint_text='seconds', label='sync sales interval', input_filter=ft.NumbersOnlyInputFilter(), keyboard_type=ft.KeyboardType.NUMBER, expand=True, value=page.client_storage.get('sync_sales_interval') or '300')
        self.basket_font_size = ft.TextField(hint_text='basket font size', label='basket font size', input_filter=ft.NumbersOnlyInputFilter(), keyboard_type=ft.KeyboardType.NUMBER, expand=True, value=page.client_storage.get('basket_font_size') or '16')
        self.scales_port = ft.TextField(hint_text='/dev/ttyS0', label='scales RS232', expand=True, value=page.client_storage.get('scales_port'))
        self.scales_baud = ft.TextField(hint_text='9600', label='scales baud', expand=True, value=page.client_storage.get('scales_baud'))
        self.scales_timeout = ft.TextField(hint_text='0.5', label='scales timeout', expand=True, value=page.client_storage.get('scales_timeout'))
        self.scales_wait_read = ft.TextField(hint_text='1', label='scales wait', expand=True, value=page.client_storage.get('scales_wait_read'))
        self.scales_ratio = ft.TextField(hint_text='1000', label='ratio', expand=True, value=page.client_storage.get('scales_ratio'))
        self.scales_unit_ids = ft.TextField(hint_text='1,2,3', label='units', expand=True, value=page.client_storage.get('scales_unit_ids'))
        self.search_auto_min_count = ft.TextField(hint_text='2', label='🔍 min', expand=True, value=page.client_storage.get('search_auto_min_count'))
        self.search_auto_limit = ft.TextField(hint_text='1000', label='🔍 limit', expand=True, value=page.client_storage.get('search_auto_limit'))
        useordercustomerdialog = page.client_storage.get('use_order_customer_dialog')
        if useordercustomerdialog is None:
            useordercustomerdialog = True
        self.use_order_customer_dialog = ft.Checkbox(label='use order customer dialog', expand=True, value=useordercustomerdialog)
        self.use_sale_customer_dialog = ft.Checkbox(label='use sale customer dialog', expand=True, value=page.client_storage.get('use_sale_customer_dialog') or False)
        useinternalscanner = page.client_storage.get('use_internal_scanner')
        if useinternalscanner is None:
            useinternalscanner = True
        self.use_internal_scanner = ft.Checkbox(label='use internal scanner', expand=True, value=useinternalscanner)
        self.translation_language = ft.TextField(label='translation language', expand=True, value=page.client_storage.get('translation_language') or locale.getlocale())
        self.content = ft.Column(controls=[
            ft.Row([self.protocol, self.port]),
            ft.Row([self.host]),
            ft.Row([self.login]),
            ft.Row([self.password]),
            ft.Row([self.network_timeout_get_product]),
            ft.Row([self.db_file_name]),
            ft.Row([self.sync_products_interval, self.sync_sales_interval]),
            ft.Row([self.basket_font_size]),
            ft.Row([self.scales_port]),
            ft.Row([self.scales_baud, self.scales_timeout]),
            ft.Row([self.scales_wait_read, self.scales_ratio]),
            ft.Row([self.scales_unit_ids]),
            ft.Row([self.search_auto_min_count, self.search_auto_limit]),
            ft.Row([self.use_order_customer_dialog]),
            ft.Row([self.use_sale_customer_dialog]),
            ft.Row([self.use_internal_scanner]),
            ft.Row([self.translation_language])
            ]
        )
        self.actions = [
            SettingsDialogAction('save', is_ok=True, on_click=self.handle_action_click),
            SettingsDialogAction('cancel', on_click=self.handle_action_click)
        ]

    def log(self, lvl=LN, msgs=[], *args, **kwargs):
        s = f'{LICONS[lvl]}::{__name__}.{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        for m in msgs:
            s += f'::{m}'
            if hasattr(m, '__traceback__'):
                s += f'🇱🇮🇳🇪{m.__traceback__.tb_lineno}'
        logging.log(lvl, s, *args, **kwargs)

    def handle_action_click(self, evt):
        if evt.control.is_ok:
            self.page.client_storage.set('protocol', self.protocol.value)
            self.page.client_storage.set('host', self.host.value)
            self.page.client_storage.set('port', self.port.value)
            self.page.client_storage.set('login', self.login.value)
            self.page.client_storage.set('password', self.password.value)
            self.page.client_storage.set('network_timeout_get_product', self.network_timeout_get_product.value)
            self.page.client_storage.set('db_file_name', self.db_file_name.value)
            self.page.client_storage.set('sync_products_interval', self.sync_products_interval.value)
            self.page.client_storage.set('sync_sales_interval', self.sync_sales_interval.value)
            self.page.client_storage.set('basket_font_size', self.basket_font_size.value)
            self.page.client_storage.set('scales_port', self.scales_port.value)
            self.page.client_storage.set('scales_baud', self.scales_baud.value)
            self.page.client_storage.set('scales_timeout', self.scales_timeout.value)
            self.page.client_storage.set('scales_wait_read', self.scales_wait_read.value)
            self.page.client_storage.set('scales_ratio', self.scales_ratio.value)
            self.page.client_storage.set('scales_unit_ids', self.scales_unit_ids.value)
            self.page.client_storage.set('search_auto_min_count', self.search_auto_min_count.value)
            self.page.client_storage.set('search_auto_limit', self.search_auto_limit.value)
            self.page.client_storage.set('use_order_customer_dialog', self.use_order_customer_dialog.value)
            self.page.client_storage.set('use_sale_customer_dialog', self.use_sale_customer_dialog.value)
            self.page.client_storage.set('use_internal_scanner', self.use_internal_scanner.value)
            self.page.client_storage.set('translation_language', self.translation_language.value)
            if self.page.http_conn.http_protocol != self.protocol.value:
                self.page.http_conn.http_protocol = self.protocol.value or 'http://'
            if self.page.http_conn.http_host != self.host.value:
                self.page.http_conn.http_host = self.host.value
            if self.page.http_conn.http_port != self.port.value:
                self.page.http_conn.http_port = self.port.value
            if self.page.http_conn.http_login != self.login.value:
                self.page.http_conn.http_login = self.login.value
            if self.page.http_conn.http_password != self.password.value:
                self.page.http_conn.http_password = self.password.value
            if self.page.http_conn.auth(True) == 200:
                self.page.run_thread(sync_products, self.page)
            set_locale(self.translation_language.value, locale_dir=self.page.directory_locale)
        self.page.close(evt.control.parent)
