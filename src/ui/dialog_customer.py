import flet, sys

from log_tools import *
from background_tasks import sync_customers


class SettingsDialogAction(flet.CupertinoDialogAction):
    def __init__(self, *args, **kwargs):
        self.is_ok = kwargs.pop('is_ok', False)
        if self.is_ok:
            kwargs['is_destructive_action'] = True
        if 'is_default_action' not in kwargs:
            kwargs['is_default_action'] = False
        super().__init__(*args, **kwargs)


class CustomerDialog(flet.CupertinoAlertDialog):
    def __init__(self, *args, **kwargs):
        self.doc_type = kwargs.pop('doc_type', '')
        super().__init__(*args, **kwargs)
        #self.title = flet.TextField('Select Customer Dialog')

        self.search_list_view = flet.ListView()

        self.search_bar = flet.SearchBar(bar_hint_text='Search customers...',
            tooltip = 'Search customers in local base',
            #on_submit = self.on_search,
            on_tap = self.open_autocomplete,
            on_change = self.on_search_change,
            on_tap_outside_bar = self.close_autocomplete,
            controls = [self.search_list_view],
            autofocus = True,
            expand = True
        )

        self.customer_new = flet.TextField(hint_text='new customer', label='new customer', expand=True)

        self.content = flet.Column(controls=[
            flet.Row([self.search_bar]),
            flet.Row([self.customer_new])
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

    def handle_action_click(self, e):
        if e.control.is_ok:
            self.log(LD, ['🍪IS_OK🍪', self.customer_new.value])
            if self.customer_new.value:
                self.page.basket.customer = self.customer_new.value
                if self.page.http_conn.post_customer(self.page.basket.customer):
                    self.page.run_thread(sync_customers, self.page)
            self.page.update_status_ctrl({5:f'👨{self.page.basket.customer}'})
            if self.doc_type and len(self.page.basket.controls):
                self.page.run_thread(self.page.basket.send_data, self.doc_type)
        self.page.close(e.control.parent)

    def open_autocomplete(self, evt):
        self.search_bar.open_view()

    def close_autocomplete(self, evt):
        self.search_bar.close_view()

    def on_search(self, evt: flet.ControlEvent):
        self.log(LD, ['👨', evt.control.data])
        if evt.control.data:
            self.page.basket.data['customer'] = evt.control.data
            self.page.update_status_ctrl({5:f'👨{self.page.basket.customer}'})
            self.search_bar.close_view()
            self.search_bar.focus()
            self.search_bar.value = self.page.basket.customer
            self.search_bar.update()
            #self.page.close(self)

    def search_close_autocompletes(self, value: str = '', only_clear: bool = False):
        if self.search_list_view.controls:
            self.search_list_view.controls = []
            if not only_clear:
                self.search_bar.close_view()
            if value:
                self.search_bar.value = value
            self.page.update_status_ctrl({5:'👨'})
            self.search_bar.update()

    def on_search_change(self, evt):
        if len(evt.data) < (self.page.client_storage.get('search_auto_min_count') or 2):
            self.search_close_autocompletes(evt.data)
        else:
            customers, msg = self.page.db_conn.search_customers(evt.data, limit_expression=f' LIMIT {self.page.client_storage.get('search_auto_limit') or 1000}')
            if customers:
                self.page.update_status_ctrl({5:f'👨{len(customers)}'})
                self.search_list_view.controls = [flet.ListTile(title=flet.Text(customer['name']), on_click=self.on_search, data=customer) for customer in customers]
                self.search_bar.open_view()
                self.search_bar.update()
            else:
                self.search_close_autocompletes(evt.data, True)
