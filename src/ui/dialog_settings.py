import flet as ft

import logging


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
        #self.title = ft.TextField('SettingsDialog')
        self.protocol = ft.TextField(hint_text='protocol', label='protocol', expand=True, value=page.client_storage.get('protocol'))
        self.host = ft.TextField(hint_text='host', label='host', expand=True, value=page.client_storage.get('host'))
        self.port = ft.TextField(hint_text='port', label='port', input_filter=ft.NumbersOnlyInputFilter(), keyboard_type=ft.KeyboardType.NUMBER, expand=True, value=page.client_storage.get('port'))
        self.login = ft.TextField(hint_text='login', label='login', expand=True, value=page.client_storage.get('login'))
        self.password = ft.TextField(hint_text='password', label='password', password=True, can_reveal_password=True, expand=True, value=page.client_storage.get('password'))
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
        self.content = ft.Column(controls=[
            ft.Row([self.protocol, self.port]),
            ft.Row([self.host]),
            ft.Row([self.login]),
            ft.Row([self.password]),
            ft.Row([self.db_file_name]),
            ft.Row([self.sync_products_interval, self.sync_sales_interval]),
            ft.Row([self.basket_font_size]),
            ft.Row([self.scales_port]),
            ft.Row([self.scales_baud, self.scales_timeout]),
            ft.Row([self.scales_wait_read, self.scales_ratio]),
            ft.Row([self.scales_unit_ids])
            ]
        )
        self.actions = [
            SettingsDialogAction('save', is_ok=True, on_click=self.handle_action_click),
            SettingsDialogAction('cancel', on_click=self.handle_action_click)
        ]

    def handle_action_click(self, e):
        if e.control.is_ok:
            self.page.client_storage.set('protocol', self.protocol.value)
            self.page.client_storage.set('host', self.host.value)
            self.page.client_storage.set('port', self.port.value)
            self.page.client_storage.set('login', self.login.value)
            self.page.client_storage.set('password', self.password.value)
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
            if self.page.http_conn.auth(True) == 200:
                self.page.run_thread(self.page.sync_products)
        self.page.close(e.control.parent)
