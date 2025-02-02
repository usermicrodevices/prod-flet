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
        self.content = ft.Column(controls=[
            ft.Row([self.protocol, self.port]),
            ft.Row([self.host]),
            ft.Row([self.login]),
            ft.Row([self.password]),
            ft.Row([self.db_file_name]),
            ft.Row([self.sync_products_interval, self.sync_sales_interval]),
            ft.Row([self.basket_font_size])
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
            self.page.sync_products()
        self.page.close(e.control.parent)
