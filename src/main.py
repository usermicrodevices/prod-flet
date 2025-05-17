import asyncio, gettext, inspect, locale, os, platform
from time import sleep
from threading import current_thread

import flet as ft
try:
    import flet_permission_handler as fph
except:
    fph = None

from log_tools import *
from hardware import mer328ac
from http_connector import HttpConnector
from db_connector import DbConnector
from ui.dialog_about import AboutDialog
from ui.dialog_settings import SettingsDialog
from ui.dialog_products import ProductsDialog
from ui.dialog_documents import DocumentsDialog
from ui.dialog_customer import CustomerDialog
from ui.control_basket import BasketControl
from background_tasks import sync_products, sync_sales, sync_customers

if ft.utils.platform_utils.is_mobile() and platform.system() in ['Linux', 'Android']:
    from fletzxing import ScanSuccessEvent, FletZxing
elif not ft.utils.platform_utils.is_mobile():
    from camera import CameraMaster

from translation import set_locale, _


async def main(page: ft.Page):

    page.title = 'PROD-CLIENT'
    page.adaptive = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.maximized = True
    page.theme_mode = ft.ThemeMode.LIGHT

    page.directory_locale = f'locale'
    if not os.path.isdir(page.directory_locale):
        os.mkdir(page.directory_locale)
    gettext.bindtextdomain('prod', page.directory_locale)
    #page._ = gettext.Catalog('prod', page.directory_locale).gettext

    ph = None
    if fph:
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
                               ft.Text(size=size_status_text, value='💬'),
                               ft.Text(size=size_status_text, value='👨')])

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
            if hasattr(page.scan_img, 'content'):
                page.scan_img.content = None
            if hasattr(page.scan_img, 'close'):
                page.scan_img.close()
            page.scan_img = None
            update_status_ctrl({3:'📴'})
    page.scan_barcode_close = scan_barcode_close

    def search_switch():
        if page.bar_search_products.on_change:
            search_close_autocompletes()
            page.bar_search_products.on_change = None
            page.bar_search_products.on_tap = None
            update_status_ctrl({4:'🎮'})
        else:
            page.bar_search_products.on_change = on_search_change
            page.bar_search_products.on_tap = open_autocomplete
            page.bar_search_products.update()
            update_status_ctrl({4:'💬'})

    def scan_barcode(evt: ft.ControlEvent):
        if page.client_storage.get('use_internal_scanner'):
            ismobile = ft.utils.platform_utils.is_mobile()
            if ismobile and fph and ph:
                if not ph.check_permission(fph.PermissionType.CAMERA, 5):
                    ph.request_permission(fph.PermissionType.CAMERA)
            if not page.scan_img:
                if ismobile:
                    def on_scansuccess(evt: ScanSuccessEvent):
                        logging.debug(f'‼📽ZXING VERSION: {evt.control.version}; ‼📹DATA: {evt.data}')
                        update_status_ctrl({3:'📹'})
                        code = eval(evt.data).get('value', '')
                        if code:
                            product_add(code)
                        page.scan_barcode_close()
                        page.scan_img = None
                    page.scan_img = ft.Container(height=200, width=400, alignment=ft.alignment.center, bgcolor=ft.Colors.GREY_200, content=FletZxing(on_scan_success=on_scansuccess))
                    update_status_ctrl({3:'🎦'})#📷📹
                    content_panel.controls.insert(0, page.scan_img)
                    content_panel.update()
                else:
                    page.scan_img = CameraMaster(reader_callback=product_add, width=320, height=240, expand=True)
                    if not page.scan_img.cap:
                        update_status_ctrl({3:'📴'})#📽
                    else:
                        update_status_ctrl({3:'🎦'})#📷📹
                        content_panel.controls.insert(0, page.scan_img)
                        content_panel.update()
            else:
                page.scan_barcode_close()
                page.scan_img = None
        search_switch()

    page.db_conn = None
    page.http_conn = None
    page.products = {}
    page.scales = None
    page.scales_unit_ids = []

    page.sync_products_running = False
    page.sync_customers_running = False

    def after_page_loaded(page):
        logging.debug('PAGE NOW IS LOADED. NEXT CHECK LOCAL DATABASE CONNECTION...')
        clocale = page.client_storage.get('translation_language') or locale.getlocale()
        set_locale(clocale, locale_dir=page.directory_locale)
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
        sync_products(page)
        sync_customers(page)
    page.run_thread(after_page_loaded, page)

    def infinity_sync_cache():
        self_name = f'{current_thread().name}.{inspect.stack()[0][3]}'
        logging.debug(f'⏰ RUN {self_name}... ⏰')
        while True:
            sync_products_interval = 7200
            try:
                sync_products_interval = int(page.client_storage.get('sync_products_interval'))
            except Exception as e:
                logging.error(e)
            logging.debug(f'⌛♾ {self_name} {sync_products_interval} SECONDS WAIT... ♾⌛')
            sleep(sync_products_interval)
            ############################
            if page.sync_products_running:
                logging.debug(f'⌛♾ {self_name} SYNC PRODUCTS IS RUNNING NOW, WAIT NEXT TIME INTERVAL ♾⌛')
            else:
                logging.debug(f'⌛♾⏰ {self_name} RUN SYNC PRODUCTS... ⏰♾⌛')
                sync_products(page)
                logging.debug(f'⌛♾ {self_name} SYNC PRODUCTS FINISHED ♾⌛')
            ############################
            if page.sync_customers_running:
                logging.debug(f'⌛♾ {self_name} SYNC CUSTOMERS IS RUNNING NOW, WAIT NEXT TIME INTERVAL ♾⌛')
            else:
                logging.debug(f'⌛♾⏰ {self_name} RUN SYNC CUSTOMERS... ⏰♾⌛')
                sync_customers(page)
                logging.debug(f'⌛♾ {self_name} SYNC CUSTOMERS FINISHED ♾⌛')
    page.run_thread(infinity_sync_cache)

    def infinity_sync_sales():
        self_name = f'{current_thread().name}.{inspect.stack()[0][3]}'
        logging.debug(f'⌛♾⏰ RUN {self_name}... ⏰♾⌛')
        while True:
            sync_sales_interval = 300
            try:
                sync_sales_interval = int(page.client_storage.get('sync_sales_interval'))
            except Exception as e:
                logging.error(e)
            logging.debug(f'⌛♾ {self_name} {sync_sales_interval} SECONDS WAIT... ♾⌛')
            sleep(sync_sales_interval)
            if page.sync_products_running:
                logging.debug(f'⌛♾ {self_name} SYNC SALES IS RUNNING NOW, WAIT NEXT TIME INTERVAL ♾⌛')
            else:
                logging.debug(f'⌛♾⏰ {self_name} RUN SYNC SALES... ⏰♾⌛')
                sync_sales(page)
                logging.debug(f'⌛♾ {self_name} SYNC SALES FINISHED, WAIT NEXT TIME INTERVAL ♾⌛')
    page.run_thread(infinity_sync_sales)

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

    page.is_search_bar_focused = True
    def on_focus_search_bar(evt):
        page.is_search_bar_focused = True

    page.bar_search_products = ft.SearchBar(bar_hint_text='Search products...',
        tooltip = 'Search products in local base',
        on_submit = on_search,
        on_tap = open_autocomplete,
        on_tap_outside_bar = close_autocomplete,
        expand = 3,
        autofocus = True,
        controls = [search_lv],
        on_change = on_search_change,
        on_focus = on_focus_search_bar
    )

    page.basket = BasketControl(page=page,
        expand_icon_color = ft.Colors.GREEN,
        elevation = 4,
        divider_color=ft.Colors.GREEN,
        spacing = 0
    )

    page.customer_dialog = None

    def basket_order_customer(evt: ft.ControlEvent = None):
        if page.client_storage.get('use_order_customer_dialog'):
            if not page.customer_dialog:
                page.customer_dialog = CustomerDialog(doc_type='order_customer')
            if page.customer_dialog and not page.customer_dialog.open:
                page.open(page.customer_dialog)
        else:
            if len(page.basket.controls):
                page.run_thread(page.basket.send_data, 'order_customer')

    def basket_sale(evt: ft.ControlEvent = None):
        if page.client_storage.get('use_sale_customer_dialog'):
            if not page.customer_dialog:
                page.customer_dialog = CustomerDialog(doc_type='sale')
            if page.customer_dialog and not page.customer_dialog.open:
                page.open(page.customer_dialog)
        else:
            if len(page.basket.controls):
                page.run_thread(page.basket.send_data)

    def basket_order(evt: ft.ControlEvent = None):
        if page.customer_dialog:
            if page.customer_dialog.open:
                page.close(page.customer_dialog)
            page.customer_dialog = None
        if len(page.basket.controls):
            page.run_thread(page.basket.send_data, 'order')

    def basket_add_product(product: dict):
        headers, prod = page.http_conn.get_product(product['id'], network_timeout=page.client_storage.get('network_timeout_get_product') or .1)
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

    def open_documents(evt: ft.ControlEvent):
        page.open(DocumentsDialog(page=page))

    def basket_clear(evt: ft.ControlEvent):
        page.basket.clearing()

    bottomappbar_content = ft.Row(
        controls=[
            ft.IconButton(icon_size=20, icon=ft.Icons.MENU, icon_color=ft.Colors.WHITE, on_click=on_click_pagelet),
            ft.Container(page.status_ctrl, expand=True),
            ft.IconButton(icon_size=20, icon=ft.Icons.PRINT, icon_color=ft.Colors.WHITE, on_click=open_documents),
            ft.IconButton(icon_size=20, icon=ft.Icons.ADD, on_click=open_poducts),
            ft.IconButton(icon_size=20, icon=ft.Icons.DELETE, on_click=basket_clear)
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
            if not page.sync_products_running:
                cnt, msg = page.db_conn.clear_products()
                logging.debug([msg, cnt])
                page.run_thread(sync_products, page)
                #cnt, msg = page.db_conn.clear_customers()
                #logging.debug([msg, cnt])
        elif evt.control.selected_index == 3:
                page.open(AboutDialog(page=page))
        elif evt.control.selected_index == 4:
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
                ft.NavigationDrawerDestination(icon=ft.Icons.ROUNDABOUT_LEFT, label='ℹ'),
                ft.NavigationDrawerDestination(icon=ft.Icons.EXIT_TO_APP, label='🔚'),
            ],
        ),
        floating_action_button=ft.FloatingActionButton('SCAN', on_click=scan_barcode),
        floating_action_button_location=ft.FloatingActionButtonLocation.CENTER_DOCKED,
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

    def on_keyboard(evt: ft.KeyboardEvent):
        match evt.key:
            case 'Escape':
                if alert_dlg.open:
                    page.close(alert_dlg)
                if page.customer_dialog:
                    page.customer_dialog = None
            case 'Enter':
                if page.customer_dialog:
                    page.customer_dialog.send_data()
                    page.close(page.customer_dialog)
                    page.customer_dialog = None
            case 'F1':
                page.open(AboutDialog(page=page))
            case 'F2':
                if evt.ctrl:
                    del page.basket.customer
                    page.update_status_ctrl({5:f'👨{page.basket.customer}'})
                    if page.customer_dialog:
                        if page.customer_dialog.open:
                            page.close(page.customer_dialog)
                        page.customer_dialog = None
                else:
                    if not page.customer_dialog:
                        page.customer_dialog = CustomerDialog()
                    if page.customer_dialog and not page.customer_dialog.open:
                        page.open(page.customer_dialog)
            case 'F3':
                page.basket.focus_sum_final()
            case 'F4':
                page.basket.focus_count()
            case 'F5':
                search_switch()
            case 'F10':
                basket_order()
            case 'F11':
                basket_order_customer()
            case 'F12':
                basket_sale()
    page.on_keyboard_event = on_keyboard


ft.app(main)#, port=9000
