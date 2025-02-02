import asyncio, inspect
import flet as ft
from time import sleep
from threading import current_thread
from datetime import datetime

import logging
logging.basicConfig(level=logging.DEBUG)

from camera import CameraMaster
from settings_dialog import SettingsDialog
from products_dialog import ProductsDialog
from http_connector import HttpConnector
from db_connector import DbConnector


class FloatNumbersOnlyInputFilter(ft.InputFilter):
    def __init__(self):
        super().__init__(regex_string=r"^[0-9]*\.[0-9]{0,3}$")


async def main(page: ft.Page):

    page.title = 'PROD-CLIENT'
    page.adaptive = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.maximized = True
    page.theme_mode = ft.ThemeMode.LIGHT

    alert_dlg = ft.AlertDialog(modal=True, actions=[ft.TextButton('ok', on_click=lambda e: page.close(e.control.parent))])
    def alert(msg: str, caption: str = 'error'):
        alert_dlg.title = ft.Text(caption)
        alert_dlg.content = ft.Text(msg)
        page.open(alert_dlg)

    page.db_conn = None
    page.http_conn = None
    page.products = {}

    page.sync_products_running = False
    def sync_products():
        if page.sync_products_running:
            logging.debug('sync_products is running now')
            return
        page.sync_products_running = True
        if page.http_conn.auth_succes:
            prods = page.http_conn.get_products_cash()
            result, msg = page.db_conn.update_products(data=prods)
            if not result:
                logging.error(['SYNC_PRODUCTS', msg, prods])
            else:
                logging.debug(['SYNC_PRODUCTS', result, msg])
        else:
            logging.debug(['SYNC_PRODUCTS', 'AUTH NOT EXISTS'])
            status_code = page.http_conn.auth()
        page.sync_products_running = False
    page.sync_products = sync_products

    def after_page_loaded(page):
        logging.debug('PAGE NOW IS LOADED')
        page.db_conn = DbConnector(file_name=page.client_storage.get('db_file_name') or 'prod.db')
        page.http_conn = HttpConnector(page)
        status_code = page.http_conn.auth(show_alert=True)
        sync_products()
    page.run_thread(after_page_loaded, page)

    def background_sync_products():
        self_name = f'{current_thread().name}.{inspect.stack()[0][3]}'
        logging.debug(f'⏰ RUN {self_name}... ⏰')
        while True:
            sync_products_interval = 7200
            try:
                sync_products_interval = int(page.client_storage.get('sync_products_interval'))
            except Exception as e:
                logging.error(e)
            logging.debug(f'⌛⌛⌛ {self_name} {sync_products_interval} SECONDS WAIT... ⌛⌛⌛')
            sleep(sync_products_interval)
            if page.sync_products_running:
                logging.debug(f'⌛⌛⌛ {self_name} SYNC PRODUCTS IS RUNNING NOW, WAIT NEXT TIME INTERVAL ⌛⌛⌛')
            else:
                logging.debug(f'⏰ {self_name} RUN SYNC PRODUCTS... ⏰')
                sync_products()
                logging.debug(f'⌛⌛⌛ {self_name} SYNC PRODUCTS FINISHED ⌛⌛⌛')
    page.run_thread(background_sync_products)

    def sync_sales():
        recs, msg = page.db_conn.get_grouped_records()
        if not recs:
            logging.debug(msg)
        else:
            for doc_recs in recs:
                data = {'sum_final':float(doc_recs[0]['sum_final']), 'registered_at':doc_recs[0]['registered_at'].strftime('%Y-%m-%dT%H:%M:%S %z'), 'type':doc_recs[0]['doc_type']}
                records, rowids = [], []
                for rec in doc_recs:
                    record = {'product':rec['product'], 'count':rec['count'], 'price':rec['price'], 'currency_id':rec['currency']['id']}
                    records.append(record)
                    rowids.append(rec['rowid'])
                data['records'] = records
                sended = False
                if page.http_conn.auth_succes:
                    sended = page.http_conn.post_doc_cash(data)
                    logging.debug(['SALE FINISH SEND TO SERVER', sended])
                if not sended:
                    logging.debug('CONNECTION ERROR')
                    status_code = page.http_conn.auth()
                    break
                else:
                    cleared_count = page.db_conn.clear_records(rowids)
                    logging.debug(['CLEARED LOCAL RECORDS', cleared_count])

    def background_sync_sales():
        self_name = f'{current_thread().name}.{inspect.stack()[0][3]}'
        logging.debug(f'⏰ RUN {self_name}... ⏰')
        while True:
            sync_sales_interval = 300
            try:
                sync_sales_interval = int(page.client_storage.get('sync_sales_interval'))
            except Exception as e:
                logging.error(e)
            logging.debug(f'⌛⌛⌛ {self_name} {sync_sales_interval} SECONDS WAIT... ⌛⌛⌛')
            sleep(sync_sales_interval)
            if page.sync_products_running:
                logging.debug(f'⌛⌛⌛ {self_name} SYNC SALES IS RUNNING NOW, WAIT NEXT TIME INTERVAL ⌛⌛⌛')
            else:
                logging.debug(f'⏰ {self_name} RUN SYNC SALES... ⏰')
                sync_sales()
                logging.debug(f'⌛⌛⌛ {self_name} SYNC SALES FINISHED, WAIT NEXT TIME INTERVAL ⌛⌛⌛')
    page.run_thread(background_sync_sales)

    #def handle_change_expansion_panel_item(e: ft.ControlEvent):
        #logging.debug(f'{e.data}; {e.control}')

    basket_sum_final = ft.TextField('0.0', expand=1,
        content_padding=0,
        input_filter=FloatNumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.RIGHT,
        #on_change=change_basket_sum_final,
    )

    basket = ft.ExpansionPanelList(
        expand_icon_color = ft.Colors.GREEN,
        elevation = 8,
        divider_color=ft.Colors.GREEN,
        #on_change=handle_change_expansion_panel_item,
        spacing = 0,
        #controls = []
    )

    def handle_delete_expansion_panel_item(e: ft.ControlEvent):
        basket.controls.remove(e.control.data)
        page.update()

    def basket_sum_final_refresh():
        sum_final = 0.0
        for item in basket.controls:
            if item.data['ctrl_sum'].value:
                sum_final += float(item.data['ctrl_sum'].value)
        basket_sum_final.value = sum_final
        basket_sum_final.update()

    def basket_crear():
        basket.controls = []
        basket_sum_final.value = '0.0'
        page.update()

    def basket_search(product):
        for item in basket.controls:
            if product['id'] == item.data['product']['id']:
                return item
        return None

    def basket_change_count(evt: ft.ControlEvent):
        logging.debug(['CHANGE_BASKET_COUNT', evt.control.value, evt.data])
        sum_product = float(evt.control.value) * float(evt.control.data['product']['price'])
        evt.control.data['ctrl_sum'].value = f'{round(sum_product, 3)}'
        evt.control.data['ctrl_sum'].update()
        basket_sum_final_refresh()

    def basket_add(product):
        item = basket_search(product)
        if item:
            item.data['ctrl_count'].value = f'{float(item.data['ctrl_count'].value) + 1}'
            sum_product = float(item.data['ctrl_count'].value) * float(item.data['product']['price'])
            item.data['ctrl_sum'].value = f'{round(sum_product, 3)}'
        else:
            str_price = f'{product['price']}'.strip('0').strip('.')
            ctrl_price = ft.Text(str_price, text_align=ft.TextAlign.RIGHT, bgcolor=ft.Colors.GREY_100)
            ctrl_currency = ft.Text(product['currency']['name'], bgcolor=ft.Colors.GREEN_100)
            ctrl_sum = ft.Text(str_price, text_align=ft.TextAlign.RIGHT, bgcolor=ft.Colors.GREEN_100)
            ctrl_count = ft.TextField('1.0', expand=2, content_padding=0, suffix_text=product['unit']['label'],
                input_filter=FloatNumbersOnlyInputFilter(),
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.RIGHT,
                on_change=basket_change_count,
                data = {'product':product, 'ctrl_sum':ctrl_sum})
            ctrl_product = ft.Text(f"{product['name'][:20]}")
            row_controls = [
                ft.Container(ctrl_product, margin=0, padding=ft.padding.only(right=2), expand=6),
                ft.Container(ctrl_price, margin=0, padding=ft.padding.only(right=2), expand=2),
                ft.Container(ctrl_currency, margin=0, padding=ft.padding.only(right=2), expand=1),
                ctrl_count,
                ft.Container(ctrl_sum, margin=0, padding=0, expand=2)
            ]
            exp = ft.ExpansionPanel(bgcolor = ft.Colors.GREEN_100,
                header = ft.Container(ft.ListTile(title = ft.Row(row_controls, spacing=0)), margin=0, padding=0),
                data = {'product':product, 'ctrl_count':ctrl_count, 'ctrl_sum':ctrl_sum})
            exp.content = ft.ListTile(title=ft.Text(product['article']),
                subtitle=ft.Text(f"{product['name']} - {product['barcodes']}"),
                trailing=ft.IconButton(ft.Icons.DELETE, on_click=handle_delete_expansion_panel_item, data=exp))
            basket.controls.insert(0, exp)
        basket_sum_final_refresh()
        page.update()
        logging.debug(f'ADD_PRODUCT: {product}')
    page.basket_add = basket_add

    def basket_sale(evt: ft.ControlEvent):
        if not basket.controls:
            alert('basket is empty', 'warning')
        else:
            dtz_now = datetime.now().astimezone()
            data = {'sum_final':basket_sum_final.value, 'registered_at':dtz_now.strftime('%Y-%m-%dT%H:%M:%S %z'), 'type':'sale'}
            records = []
            for item in basket.controls:
                record = {'product':item.data['product']['id'], 'count':item.data['ctrl_count'].value, 'price':item.data['product']['price'], 'currency':item.data['product']['currency']}
                records.append(record)
            data['records'] = records
            sended = False
            if page.http_conn.auth_succes:
                sended = page.http_conn.post_doc_cash(data)
                logging.debug(['SALE FINISH SEND TO SERVER', sended])
            if not sended:
                logging.debug('SAVE SALE TO LOCAL DB...')
                local_records = []
                for r in records:
                    local_records.append((data['type'], dtz_now, r['product'], float(r['count']), 0.0, float(r['price']), float(data['sum_final']), r['currency']))
                result, msg = page.db_conn.insert_records(local_records)
                logging.debug(['SAVE SALE TO LOCAL DB FINISH', result, msg])
            basket_crear()

    def product_search(code: str):
        logging.info(['CODE', code])
        prod, msg = page.db_conn.get_product(code)
        logging.info(['FOUND', prod, msg])
        return prod

    def product_add(code: str):
        page.add(ft.CupertinoActivityIndicator(radius=50, color=ft.Colors.RED, animating=True))
        product = product_search(code)
        if product:
            page.basket_add(product)
        else:
            logging.debug(f'{code} NOT FOUND')
            alert(code, 'NOT FOUND')

    def on_click_pagelet(evt: ft.ControlEvent):
        logging.debug(f'ON_CLICK_PAGELET {evt.control.parent}')
        pagelet.appbar = None
        pagelet.end_drawer.open = True
        pagelet.end_drawer.update()
        page.update()

    def on_search(evt: ft.ControlEvent):
        if evt.control.value:
            product_add(evt.control.value)
            evt.control.value = ''

    def open_poducts(evt: ft.ControlEvent):
        page.open(ProductsDialog(page=page))

    bottomappbar_content = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.MENU, icon_color=ft.Colors.WHITE, on_click=on_click_pagelet),
            #ft.SearchBar(bar_hint_text="Search products...", on_tap=on_search, on_submit=on_search, expand=True, autofocus=True)
            ft.Container(expand=True),
            #ft.Container(expand=True, content=ft.Column(search_ctrl)),
            #ft.IconButton(icon=ft.Icons.SEARCH, icon_color=ft.Colors.WHITE, on_click=on_search),
            #ft.IconButton(icon=ft.Icons.PRICE_CHECK, icon_color=ft.Colors.WHITE),
            ft.IconButton(icon=ft.Icons.PRINT, icon_color=ft.Colors.WHITE),
            #ft.IconButton(icon=ft.Icons.POINT_OF_SALE, icon_color=ft.Colors.WHITE),
            ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=open_poducts),
            ft.FloatingActionButton(icon=ft.Icons.DELETE, on_click=lambda evt: basket_crear())
        ]
    )

    bottomappbar = ft.BottomAppBar(bottomappbar_content, bgcolor=ft.Colors.GREEN, shape=ft.NotchShape.CIRCULAR)

    content_panel = ft.core.list_view.ListView(controls=[basket])

    logging.debug(f'w={page.window.width:.2f}; h={page.window.height:.2f}; {page.client_ip}; {page.client_user_agent}; {page.pwa}')

    def scan_barcode(evt: ft.ControlEvent):
        img = ft.Image(src_base64='', src='', width=320, height=240)
        page.add(img)
        page.update()
        camera_master = CameraMaster(page, img, is_a_qr_reader=True, qr_reader_callback=product_add)

    def handle_dismiss_navigation_drawer(evt: ft.ControlEvent):
        logging.debug(f'DISMISS {evt.control}')
        pagelet.appbar = topbar
        page.update()

    def handle_change_navigation_drawer(evt: ft.ControlEvent):
        logging.debug(f'CHANGED {evt.control.selected_index}')
        if evt.control.selected_index == 0:
            page.open(SettingsDialog(page=page))
        elif evt.control.selected_index == 1:
            page.open(ProductsDialog(page=page))
        elif evt.control.selected_index == 2:
            if page.platform == 'android':
                import os
                os._exit(0)
            else:
                page.window.close()
        pagelet.end_drawer.open = False
        pagelet.end_drawer.update()

    bar_search_products = ft.SearchBar(bar_hint_text="Search products...",
        #on_tap=on_search,
        on_submit=on_search,
        expand=3, autofocus=True)

    topbar = ft.CupertinoAppBar(
        #title=ft.SearchBar(bar_hint_text="Search products...", on_tap=on_search, on_submit=on_search, expand=True, autofocus=True),
        #leading=ft.Icon(ft.icons.WB_SUNNY),
        #trailing=ft.Icon(ft.icons.WB_SUNNY_OUTLINED),
        middle=ft.Row([bar_search_products, basket_sum_final, ft.IconButton(icon=ft.Icons.POINT_OF_SALE, on_click=basket_sale)]),
        bgcolor=ft.Colors.GREEN_100)

    pagelet = ft.Pagelet(
        appbar=topbar,
        content=content_panel,
        bgcolor=ft.Colors.WHITE,
        bottom_app_bar=bottomappbar,
        end_drawer=ft.NavigationDrawer(
            on_dismiss=handle_dismiss_navigation_drawer,
            on_change=handle_change_navigation_drawer,
            controls=[
                ft.NavigationDrawerDestination(icon=ft.Icons.ADD_TO_HOME_SCREEN_SHARP, label='🏠'),
                ft.NavigationDrawerDestination(icon=ft.Icons.ADD_COMMENT, label='➕'),
                ft.NavigationDrawerDestination(icon=ft.Icons.EXIT_TO_APP, label='🔚'),
            ],
        ),
        floating_action_button=ft.FloatingActionButton('SCAN', on_click=scan_barcode),
        floating_action_button_location=ft.FloatingActionButtonLocation.CENTER_DOCKED,
        #width=400,
        height=page.window.height if page.window.height else 850
    )
    page.add(pagelet)

    def page_resize(evt):#not worked on android
        logging.debug(evt)
        logging.debug(f'PAGE_RESIZE: w={evt.width}; h={evt.height}; {page.pwa}')
        if evt.height:
            pagelet.height = evt.height
            page.update()
    page.on_resized = page_resize

    page.__keyboard_buffer__ = ''
    def on_keyboard(evt: ft.KeyboardEvent):
        if alert_dlg.open:
            page.close(alert_dlg)
        #if evt.key in ['Enter', 'Numpad Enter'] and page.__keyboard_buffer__:
            #product_add(page.__keyboard_buffer__)
            #page.__keyboard_buffer__ = ''
        #else:
            #data = evt.key.replace('Numpad ', '').replace('Num Lock', '')
            #if data.isdigit():
                #page.__keyboard_buffer__ += data
    page.on_keyboard_event = on_keyboard


ft.app(main)#, port=9000
