import asyncio, inspect, os
from time import sleep
from threading import current_thread

import flet as ft
import flet_permission_handler as fph

from log_tools import *
from hardware import mer328ac
from camera import CameraMaster
from http_connector import HttpConnector
from db_connector import DbConnector
from ui.dialog_settings import SettingsDialog
from ui.dialog_products import ProductsDialog
from ui.control_basket import BasketControl


async def main(page: ft.Page):

    page.title = 'PROD-CLIENT'
    page.adaptive = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.maximized = True
    page.theme_mode = ft.ThemeMode.LIGHT

    ph = fph.PermissionHandler()
    page.overlay.append(ph)

    alert_dlg = ft.AlertDialog(modal=True, actions=[ft.TextButton('ok', on_click=lambda e: page.close(e.control.parent))])
    def alert(msg: str, caption: str = 'error'):
        alert_dlg.title = ft.Text(caption)
        alert_dlg.content = ft.Text(msg)
        page.open(alert_dlg)
    page.alert = alert

    size_status_text = 45
    if ft.utils.platform_utils.is_mobile():
        size_status_text = 14
    page.status_ctrl = ft.Row([ft.Text(size=size_status_text),
                               ft.Text(size=size_status_text, value='🛒0'),
                               ft.Text(size=size_status_text, value='🗒'),
                               ft.Text(size=size_status_text, value='📴'),
                               ft.Text(size=size_status_text, value='💬')])

    def update_status_ctrl(statuses={}, redraw=True):
        if statuses:
            for k,v in statuses.items():
                page.status_ctrl.controls[k].value = v
            if redraw:
                page.status_ctrl.update()
    page.update_status_ctrl = update_status_ctrl

    def is_superuser():
        return page.client_storage.get('user').get('is_superuser', False)
    page.is_superuser = is_superuser

    page.scan_img = None
    def scan_barcode_close():
        if page.scan_img in content_panel.controls:
            content_panel.controls.remove(page.scan_img)
            content_panel.update()
        if page.scan_img:
            page.scan_img.close()
            page.scan_img = None
            update_status_ctrl({3:'📴'})
    page.scan_barcode_close = scan_barcode_close

    def scan_barcode(evt: ft.ControlEvent):
        if ft.utils.platform_utils.is_mobile():
            if not ph.check_permission(fph.PermissionType.CAMERA, 5):
                ph.request_permission(fph.PermissionType.CAMERA)
        if not page.scan_img:
            page.scan_img = CameraMaster(reader_callback=product_add, width=320, height=240, expand=True)
            if not page.scan_img.cap:
                update_status_ctrl({3:'📴'})#📽
            else:
                update_status_ctrl({3:'🎦'})#📷📹
                content_panel.controls.insert(0, page.scan_img)
                content_panel.update()
        else:
            page.scan_barcode_close()

    page.db_conn = None
    page.http_conn = None
    page.products = {}
    page.scales = None
    page.scales_unit_ids = []

    page.sync_products_running = False
    def sync_products():
        if page.sync_products_running:
            logging.debug('sync_products is running now')
            return
        page.sync_products_running = True
        if page.http_conn.auth_succes:
            def db_update_products(prods):
                count_updated = 0
                if prods:
                    count_updated, msg = page.db_conn.update_products(data=prods)
                    logging.debug(['UPDATED_PRODUCTS', count_updated, msg])
                return count_updated
            headers, prods = page.http_conn.get_products_cash()
            updated_products = db_update_products(prods)
            full_products, msg = page.db_conn.get_products_count()
            update_status_ctrl({0:f'{full_products}🧷{updated_products}'})
            page_max = int(headers.get('page_max', 0))
            logging.debug(['PAGE_MAX', page_max])
            if page_max > 1:
                for p in range(2, page_max):
                    headers, prods = page.http_conn.get_products_cash(p)
                    updated_products += db_update_products(prods)
                    full_products, msg = page.db_conn.get_products_count()
                    update_status_ctrl({0:f'{full_products}🧷{updated_products}'})
            if updated_products:
                page.db_conn.update_cache()
        else:
            logging.debug(['SYNC_PRODUCTS', 'AUTH NOT EXISTS'])
            status_code = page.http_conn.auth()
        page.sync_products_running = False
    page.sync_products = sync_products

    def after_page_loaded(page):
        logging.debug('PAGE NOW IS LOADED. NEXT CHECK LOCAL DATABASE CONNECTION...')
        page.db_conn = DbConnector(file_name=page.client_storage.get('db_file_name') or 'prod.db')
        full_products, msg = page.db_conn.get_products_count()
        update_status_ctrl({0:f'{full_products}🧷0'})#, 1:'🛒0', 2:'🗒'
        logging.debug('CHECK ACCESSIBLE RETAIL HARDWARE...')
        page.scales = mer328ac.pos2m(page.client_storage.get('scales_port') or '/dev/ttyUSB0', int(page.client_storage.get('scales_baud') or 9600), timeout=float(page.client_storage.get('scales_timeout') or 0.5), delay_requests=float(page.client_storage.get('scales_wait_read') or 0.5), weight_ratio=int(page.client_storage.get('scales_ratio') or 1000), start_infinity_read=True, exclusive=True)
        if page.scales.device:
            update_status_ctrl({2:'🖥⚖'})
        scales_unit_ids = page.client_storage.get('scales_unit_ids')
        if scales_unit_ids:
            try:
                page.scales_unit_ids = [int(uid) for uid in page.client_storage.get('scales_unit_ids').split(',')]
            except Exception as e:
                logging.error(e)
        logging.debug('CHECK REMOTE NETWORK CONNECTION...')
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
                frec = doc_recs[0]
                data = {'sum_final':float(frec['sum_final']), 'registered_at':frec['registered_at'].strftime('%Y-%m-%dT%H:%M:%S %z'), 'type':frec['doc_type'], 'customer':frec['customer']}
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
                elif rowids:
                    cleared_count, msg = page.db_conn.clear_records(rowids)
                    logging.debug(['CLEARED LOCAL RECORDS', cleared_count, msg])

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

    def open_autocomplete(evt):
        page.bar_search_products.open_view()

    def close_autocomplete(evt):
        page.bar_search_products.close_view()

    def on_search(evt: ft.ControlEvent):
        if evt.control.value:
            product_add(evt.control.value)
            evt.control.value = ''
            evt.control.update()
            evt.control.focus()

    search_lv = ft.ListView()

    def search_close_autocompletes(value: str = '', only_clear: bool = False):
        if search_lv.controls:
            search_lv.controls = []
            if not only_clear:
                page.bar_search_products.close_view()
            if value:
                page.bar_search_products.value = value
            update_status_ctrl({4:'💬'})
            page.bar_search_products.update()

    def on_search_change(evt):
        if len(evt.data) < (page.client_storage.get('search_auto_min_count') or 2):
            search_close_autocompletes(evt.data)
        else:
            products, msg = page.db_conn.search_products(evt.data, limit_expression=f' LIMIT {page.client_storage.get('search_auto_limit') or 1000}')
            if products:
                update_status_ctrl({4:f'💬{len(products)}'})
                search_lv.controls = [ft.ListTile(title=ft.Text(product['name']), on_click=lambda evt: basket_add_product(evt.control.data), data=product) for product in products]
                page.bar_search_products.open_view()
                page.bar_search_products.update()
            else:
                search_close_autocompletes(evt.data, True)

    page.bar_search_products = ft.SearchBar(bar_hint_text='Search products...',
        tooltip = 'Search products in local base',
        on_submit=on_search,
        on_tap=open_autocomplete,
        on_tap_outside_bar = close_autocomplete,
        expand=3,
        autofocus=True,
        controls=[search_lv],
        on_change=on_search_change
    )

    page.basket = BasketControl(page=page,
        expand_icon_color = ft.Colors.GREEN,
        elevation = 4,
        divider_color=ft.Colors.GREEN,
        spacing = 0
    )

    def basket_order_customer(evt: ft.ControlEvent = None):
        if len(page.basket.controls):
            page.run_thread(page.basket.send_data, 'order_customer')

    def basket_sale(evt: ft.ControlEvent = None):
        if len(page.basket.controls):
            page.run_thread(page.basket.send_data)

    def basket_add_product(product: dict):
        headers, prod = page.http_conn.get_product(product['id'])
        product['count'] = '-' if not prod else prod['count']
        page.basket.add(product)
        search_close_autocompletes()

    def product_search(code: str):
        logging.info(['CODE', code])
        prods, msg = page.db_conn.search_products(code)
        logging.info(['FOUND', prods, msg])
        return prods

    def product_add(code: str):
        page.add(ft.CupertinoActivityIndicator(radius=50, color=ft.Colors.RED, animating=True))
        products = product_search(code)
        if len(products) == 1:
            basket_add_product(products[0])
        elif products:
            logging.debug(f'{code} FOUND MANY')
            alert(code, 'FOUND MANY, PLEASE SELECT ONE')
        else:
            logging.debug(f'{code} NOT FOUND')
            alert(code, 'NOT FOUND')

    def on_click_pagelet(evt: ft.ControlEvent):
        logging.debug(f'ON_CLICK_PAGELET {evt.control.parent}')
        pagelet.appbar = None
        pagelet.end_drawer.open = True
        pagelet.end_drawer.update()
        page.update()

    def open_poducts(evt: ft.ControlEvent):
        page.open(ProductsDialog(page=page))

    bottomappbar_content = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.MENU, icon_color=ft.Colors.WHITE, on_click=on_click_pagelet),
            #ft.SearchBar(bar_hint_text="Search products...", on_tap=on_search, on_submit=on_search, expand=True, autofocus=True)
            #ft.Container(expand=True),
            ft.Container(page.status_ctrl, expand=True),
            #ft.IconButton(icon=ft.Icons.SEARCH, icon_color=ft.Colors.WHITE, on_click=on_search),
            #ft.IconButton(icon=ft.Icons.PRICE_CHECK, icon_color=ft.Colors.WHITE),
            ft.IconButton(icon=ft.Icons.PRINT, icon_color=ft.Colors.WHITE),
            ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=open_poducts),
            ft.FloatingActionButton(icon=ft.Icons.DELETE, on_click=lambda evt: page.basket.clearing())
        ]
    )

    bottomappbar = ft.BottomAppBar(bottomappbar_content, bgcolor=ft.Colors.GREEN, shape=ft.NotchShape.CIRCULAR)

    content_panel = ft.ListView(controls=[page.basket])

    logging.debug(f'w={page.window.width:.2f}; h={page.window.height:.2f}; {page.client_ip}; {page.client_user_agent}; {page.pwa}')

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
            page.db_conn.clear_local_products()
            sync_products()
        elif evt.control.selected_index == 3:
            page.client_storage.set('user', {})
            if page.platform == 'android':
                import os
                os._exit(0)
            else:
                page.window.close()
        pagelet.end_drawer.open = False
        pagelet.end_drawer.update()

    topbar = ft.CupertinoAppBar(
        #title=ft.SearchBar(bar_hint_text="Search ...", on_submit=on_search),
        #leading=ft.Icon(ft.icons.WB_SUNNY),
        #trailing=ft.Icon(ft.icons.WB_SUNNY_OUTLINED),
        middle=ft.Row([
            page.bar_search_products,
            ft.IconButton(icon=ft.Icons.SHOPPING_BASKET, on_click=basket_order_customer),
            page.basket.sum_final,
            ft.IconButton(icon=ft.Icons.POINT_OF_SALE, on_click=basket_sale)
            ]),
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
                ft.NavigationDrawerDestination(icon=ft.Icons.LOCK_RESET, label='🔄'),
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
        if evt.key == 'Escape':
            if alert_dlg.open:
                page.close(alert_dlg)
        if evt.key == 'F12':
            basket_sale()
        if evt.key == 'F11':
            basket_order_customer()
        if evt.key == 'F5':
            if page.bar_search_products.on_change:
                page.bar_search_products.on_change = None
                search_close_autocompletes()
                update_status_ctrl({4:'🎮'})
            else:
                page.bar_search_products.on_change = on_search_change
                page.bar_search_products.update()
                update_status_ctrl({4:'💬'})
        #elif evt.key in ['Enter', 'Numpad Enter'] and page.__keyboard_buffer__:
            #product_add(page.__keyboard_buffer__)
            #page.__keyboard_buffer__ = ''
        #else:
            #data = evt.key.replace('Numpad ', '').replace('Num Lock', '')
            #if data.isdigit():
                #page.__keyboard_buffer__ += data
    page.on_keyboard_event = on_keyboard


ft.app(main)#, port=9000
