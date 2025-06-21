import flet as ft, sys

from datetime import datetime

from log_tools import *


class FloatNumbersOnlyInputFilter(ft.InputFilter):
    def __init__(self):
        super().__init__(regex_string=r"^[0-9]*\.[0-9]{0,3}$")


class BasketControl(ft.ExpansionPanelList):

    sum_final = ft.TextField('0.0', expand=1,
        content_padding=0,
        input_filter=FloatNumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.RIGHT
    )

    def __init__(self, *args, **kwargs):
        self.page = kwargs.pop('page')
        #kwargs['on_change'] = self.handle_change_expansion_panel_item
        if 'data' not in kwargs:
            kwargs['data'] = {'customer': {'id':None, 'name':'', 'extinfo':{}}}
        elif 'customer' not in kwargs['data']:
            kwargs['data']['customer'] = {'id':None, 'name':'', 'extinfo':{}}
        self.sum_final.on_focus = self.on_focus_sum_final
        super().__init__(*args, **kwargs)

    def log(self, lvl=LN, msgs=[], *args, **kwargs):
        s = f'{LICONS[lvl]}::{__name__}.{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        for m in msgs:
            s += f'::{m}'
            if hasattr(m, '__traceback__'):
                s += f'🇱🇮🇳🇪{m.__traceback__.tb_lineno}'
        logging.log(lvl, s, *args, **kwargs)

    #def handle_change_expansion_panel_item(self, evt: ft.ControlEvent):
        #self.log(LD, [evt.data, evt.control])

    @property
    def customer(self):
        return self.data['customer']['name']

    @customer.setter
    def customer(self, value):
        if value:
            self.data['customer']['name'] = value

    @customer.deleter
    def customer(self):
        self.data['customer'] = {'id':None, 'name':'', 'extinfo':{}}

    def update_status_count(self, redraw_ctrl=True):
        self.page.update_status_ctrl({1:f'🛒{len(self.controls)}'}, redraw_ctrl)

    def clearing(self):
        self.controls = []
        self.update_status_count(False)
        self.sum_final.value = '0.0'
        del self.customer
        self.page.update_status_ctrl({5:'👨'}, False)
        self.page.update()
        self.page.bar_search_products.focus()

    def sum_final_refresh(self):
        self.page.scan_barcode_close()
        sum_final = 0.0
        for item in self.controls:
            if item.data['ctrl_sum'].value:
                sum_final += float(item.data['ctrl_sum'].value)
        self.sum_final.value = round(sum_final, 2)
        self.sum_final.update()

    def search(self, product):
        for item in self.controls:
            if product['id'] == item.data['product']['id']:
                return item
        return None

    def on_change_product_count(self, evt: ft.ControlEvent):
        self.log(LD, ['CHANGE_BASKET_COUNT', evt.control.value, evt.data])
        c = evt.control
        sum_product = round(float(c.value) * float(c.data['ctrl_price'].value), 2)
        c.data['ctrl_sum'].value = f'{sum_product}'
        c.data['ctrl_sum'].update()
        self.sum_final_refresh()

    def on_change_product_price(self, evt: ft.ControlEvent):
        self.log(LD, ['CHANGE_BASKET_PRICE', evt.control.value, evt.data])
        c = evt.control
        sum_product = round(float(c.value) * float(c.data['ctrl_count'].value), 2)
        c.data['ctrl_sum'].value = f'{sum_product}'
        c.data['ctrl_sum'].update()
        self.sum_final_refresh()

    def on_click_delete_item(self, evt: ft.ControlEvent):
        self.controls.remove(evt.control.data)
        self.update_status_count()
        self.update()

    def on_focus_sum_final(self, evt: ft.ControlEvent):
        self.page.is_search_bar_focused = False

    def on_focus_price(self, evt: ft.ControlEvent):
        self.page.is_search_bar_focused = False

    def on_focus_count(self, evt: ft.ControlEvent):
        self.page.is_search_bar_focused = False

    def add(self, product):
        item = self.search(product)
        new_counts = 1.0
        if product.get('unit', {}).get('id', 0) in self.page.scales_unit_ids and self.page.scales and self.page.scales.data["weight"]:
                new_counts = self.page.scales.data["weight"]
        if item:
            item.data['ctrl_count_from_server'].value = product.get('count', '-')
            count_old = float(item.data['ctrl_count'].value) if item.data['ctrl_count'].value else 0.0
            if new_counts == 1.0:
                item.data['ctrl_count'].value = f'{count_old + new_counts}'
            else:
                item.data['ctrl_count'].value = f'{new_counts}'
            count = float(item.data['ctrl_count'].value) if item.data['ctrl_count'].value else 0.0
            price = float(item.data['ctrl_price'].value) if item.data['ctrl_price'].value else 0.0
            sum_product = round(count * price, 2)
            item.data['ctrl_sum'].value = f'{sum_product}'
        else:
            font_size = int(self.page.client_storage.get('basket_font_size'))
            ctrl_count_from_server = ft.Text(product.get('count', '-'), text_align=ft.TextAlign.LEFT, bgcolor=ft.Colors.GREY_300, size=font_size)
            str_price = f'{product['price']:.2f}'#.strip('0').strip('.')
            if not str_price:
                str_price = '0.0'
            ctrl_currency = ft.Text(product['currency']['name'], size=font_size-2)
            sum_product = round(product['price']*new_counts, 2)
            ctrl_sum = ft.Text(str_price if new_counts == 1.0 else f'{sum_product}', text_align=ft.TextAlign.RIGHT, bgcolor=ft.Colors.GREEN_100, size=font_size, weight=ft.FontWeight.W_900)
            if self.page.is_superuser():
                ctrl_price = ft.TextField(str_price,
                    content_padding=0,
                    text_size=font_size,
                    input_filter=FloatNumbersOnlyInputFilter(),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    text_align=ft.TextAlign.RIGHT,
                    on_change=self.on_change_product_price,
                    on_focus = self.on_focus_price,
                    data = {'ctrl_sum':ctrl_sum})
            else:
                ctrl_price = ft.Text(str_price,
                    text_align=ft.TextAlign.RIGHT,
                    bgcolor=ft.Colors.GREY_100,
                    size=font_size,
                    data = {'ctrl_sum':ctrl_sum})
            ctrl_count = ft.TextField(f'{new_counts}',
                expand=3,
                text_size=font_size,
                content_padding=0,
                #suffix_text=product['unit']['label'],
                input_filter=FloatNumbersOnlyInputFilter(),
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.RIGHT,
                on_change=self.on_change_product_count,
                on_focus = self.on_focus_count,
                data = {'ctrl_price':ctrl_price, 'ctrl_sum':ctrl_sum})
            ctrl_price.data['ctrl_count'] = ctrl_count
            ctrl_product = ft.Text(f"{product['name']}", size=font_size)
            ctrl_unit = ft.Text(product['unit']['label'], size=font_size-2)
            subtitle_controls = [
                ft.Container(ctrl_count_from_server, margin=0, padding=ft.padding.only(right=2), expand=3),
                ft.Container(ctrl_price, margin=0, padding=ft.padding.only(right=2), expand=3),
                ft.Container(ctrl_currency, margin=0, padding=ft.padding.only(right=2), expand=1),
                ctrl_count,
                ft.Container(ctrl_unit, margin=0, padding=ft.padding.only(left=2), expand=1),
                ft.Container(ctrl_sum, margin=0, padding=0, expand=3),
                ft.Container(ctrl_currency, margin=0, padding=ft.padding.only(right=2), expand=1)
            ]
            exp = ft.ExpansionPanel(bgcolor = ft.Colors.GREEN_100,
                header = ft.Container(ft.ListTile(
                    title = ft.Row([ctrl_product], spacing=0),
                    subtitle = ft.Row(subtitle_controls, spacing=0)
                    ), margin=0, padding=0),
                data = {'product':product, 'ctrl_count_from_server':ctrl_count_from_server, 'ctrl_count':ctrl_count, 'ctrl_price':ctrl_price, 'ctrl_sum':ctrl_sum})
            exp.content = ft.ListTile(title=ft.Text(product['article']),
                subtitle=ft.Text(f"{product['name']} - {product['barcodes']}"),
                trailing=ft.IconButton(ft.Icons.DELETE, on_click=self.on_click_delete_item, data=exp))
            self.controls.insert(0, exp)
            self.update_status_count(False)
        self.sum_final_refresh()
        self.page.update()
        self.log(LD, ['ADD_PRODUCT: ', product])

    def send_data(self, data_type: str = 'sale'):
        if not self.controls:
            alert('basket is empty', 'warning')
        else:
            dtz_now = datetime.now().astimezone()
            data = {'sum_final':self.sum_final.value, 'registered_at':dtz_now.strftime('%Y-%m-%dT%H:%M:%S %z'), 'type':data_type, 'customer':self.data.get('customer', {})}
            records = []
            for item in self.controls:
                record = {'product':item.data['product']['id'], 'count':item.data['ctrl_count'].value, 'price':item.data['product']['price'], 'currency':item.data['product']['currency']}
                records.append(record)
            data['records'] = records
            sended = False
            if self.page.http_conn.auth_success:
                sended = self.page.http_conn.post_doc_cash(data)
                self.log(LD, ['SALE FINISH SEND TO SERVER', sended])
            if not sended:
                self.log(LD, ['SAVE SALE TO LOCAL DB...'])
                local_records = []
                for r in records:
                    r['sum_final'] = data['sum_final']
                    r['registered_at'] = dtz_now
                    r['doc_type'] = data['type']
                    r['cost'] = 0.0
                    r['customer'] = data['customer']
                    local_records.append(r)
                result, msg = self.page.db_conn.insert_records(local_records)
                self.log(LD, ['SAVE SALE TO LOCAL DB FINISH', result, msg])
                if not result:
                    self.log(LW, [msg])
            self.clearing()

    def focus_sum_final(self, index=0):
        if self.page.is_search_bar_focused:
            try:
                self.sum_final.focus()
            except Exception as e:
                self.log(LE, [e])
        else:
            self.page.bar_search_products.focus()

    def focus_count(self, index=0):
        if self.page.is_search_bar_focused and self.controls:
            try:
                self.controls[index].data['ctrl_count'].focus()
            except Exception as e:
                self.log(LE, [e])
        else:
            self.page.bar_search_products.focus()
