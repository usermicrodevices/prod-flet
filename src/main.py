import argparse
argsparser = argparse.ArgumentParser(prog='PROD-FLET', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argsparser.add_argument('--clear_preferences', default=argparse.SUPPRESS, help='clear shared preferences')
argsparser.print_help()
print('Sorry, but now "flet run" not support redirect application cli args\n\n')


import asyncio, gettext, inspect, locale, os, platform, sys
from time import sleep
from threading import current_thread

import flet

#flet.context.disable_auto_update() # NOT USED FROM FLET 0.80.5

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
from background_tasks import sync_products, sync_sales, sync_customers, get_prefs_value

if flet.utils.platform_utils.is_mobile() and platform.system() in ['Linux', 'Android']:
    from fletzxing import ScanSuccessEvent, FletZxing
elif not flet.utils.platform_utils.is_mobile():
    from camera import CameraMaster

from translation import set_locale, _



async def main(page: flet.Page):

    appargs = argsparser.parse_args()

    preferences = flet.SharedPreferences()

    if hasattr(appargs, 'clear_preferences'):
        logging.debug(f'🛠️⚙ CLEAR PREFERENCES... ⚙🛠️')
        await preferences.clear()
    else:
        logging.debug(f'⚡🏃 {sys.argv} 🏃⚡')
    #await preferences.clear()
    logging.debug(f'🔑PREFERENCES.GET_KEYS {await preferences.get_keys("")} 🔑')

    page.version = '1.1.2'
    page.title = 'PROD-CLIENT'
    page.adaptive = True
    page.vertical_alignment = flet.MainAxisAlignment.CENTER
    page.window.maximized = True
    page.theme_mode = flet.ThemeMode.LIGHT

    page.directory_locale = f'locale'
    if not os.path.isdir(page.directory_locale):
        os.mkdir(page.directory_locale)
    gettext.bindtextdomain('prod', page.directory_locale)
    #page._ = gettext.Catalog('prod', page.directory_locale).gettext

    ph = None
    if fph:
        ph = fph.PermissionHandler()
        page.overlay.append(ph)

    #alert_dlg = flet.AlertDialog(modal=True, actions=[flet.TextButton('ok', on_click=lambda e: page.pop_dialog(e.control.parent))])
    alert_dlg = flet.AlertDialog(modal=True, actions=[flet.TextButton('ok', on_click=lambda e: page.pop_dialog())])
    def alert(msg: str, caption: str = 'error'):
        alert_dlg.title = flet.Text(caption)
        alert_dlg.content = flet.Text(msg)
        page.show_dialog(alert_dlg)
    page.alert = alert

    size_status_text = 45
    if flet.utils.platform_utils.is_mobile():
        size_status_text = 14
    ctrls = [
        flet.Text(size=size_status_text),
        flet.Text(size=size_status_text, value='🛒0'),
        flet.Text(size=size_status_text, value='🗒'),
        flet.Text(size=size_status_text, value='📴'),
        flet.Text(size=size_status_text, value='💬'),
        flet.Text(size=size_status_text, value='👨')]
    page.status_ctrl = flet.GridView(controls=ctrls, max_extent=size_status_text*1.2)
    page.add(page.status_ctrl)

    def update_status_ctrl(statuses={}, redraw=True):
        if statuses:
            for k,v in statuses.items():
                page.status_ctrl.controls[k].value = v
            if redraw:
                page.status_ctrl.update()
    page.update_status_ctrl = update_status_ctrl

    async def is_superuser():
        #return await preferences.get('user').get('is_superuser', False)
        return (await get_prefs_value('user', dict, {'is_superuser':False})).get('is_superuser', False)
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

    async def scan_barcode(evt: flet.ControlEvent):
        if await preferences.get('use_internal_scanner'):
            ismobile = flet.utils.platform_utils.is_mobile()
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
                    page.scan_img = flet.Container(height=200, width=400, alignment=flet.alignment.center, bgcolor=flet.Colors.GREY_200, content=FletZxing(on_scan_success=on_scansuccess))
                    update_status_ctrl({3:'🎦'})
                    content_panel.controls.insert(0, page.scan_img)
                    content_panel.update()
                else:
                    page.scan_img = CameraMaster(reader_callback=product_add, width=320, height=240, expand=True)
                    if not page.scan_img.cap:
                        update_status_ctrl({3:'📴'})
                    else:
                        update_status_ctrl({3:'🎦'})
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

    async def after_page_loaded(page):
        logging.debug(f'PAGE NOW IS LOADED 🌍{page.locale_configuration}🌍. NEXT CHECK LOCAL DATABASE CONNECTION...')
        clocale = await preferences.get('translation_language') or locale.getlocale()
        try:
            set_locale(clocale, locale_dir=page.directory_locale)
        except Exception as e:
            logging.error(e)
            #page.alert(f'{e}')
        logging.debug('✋🎹GET DB FILE NAME...🎹✋')
        db_file_name = 'prod.db'
        if await preferences.contains_key('db_file_name'):
            db_file_name = await preferences.get('db_file_name') or db_file_name
        page.db_conn = DbConnector(file_name=db_file_name)
        logging.debug(f'✋🎹{page.db_conn}({db_file_name})🎹✋')
        full_products, msg = page.db_conn.get_products_count()
        update_status_ctrl({0:f'{full_products}🧷0'})#, 1:'🛒0', 2:'🗒'
        logging.debug('CHECK ACCESSIBLE RETAIL HARDWARE...')
        page.scales = mer328ac.pos2m(await preferences.get('scales_port') or '/dev/ttyUSB0', int(await preferences.get('scales_baud') or 9600), timeout=float(await preferences.get('scales_timeout') or 0.5), delay_requests=float(await preferences.get('scales_wait_read') or 0.5), weight_ratio=int(await preferences.get('scales_ratio') or 1000), start_infinity_read=True, exclusive=True)
        if page.scales.device:
            update_status_ctrl({2:'🖥⚖'})
        scales_unit_ids = await preferences.get('scales_unit_ids')
        if scales_unit_ids:
            try:
                page.scales_unit_ids = [int(uid) for uid in await preferences.get('scales_unit_ids').split(',')]
            except Exception as e:
                logging.error(e)
        logging.debug('CHECK REMOTE NETWORK CONNECTION...')
        page.http_conn = HttpConnector(page)
        status_code = await page.http_conn.auth(show_alert=True)
        await sync_products(page)
        await sync_customers(page)
    page.run_task(after_page_loaded, page)

    async def infinity_sync_cache():
        self_name = f'{current_thread().name}.{inspect.stack()[0][3]}'
        logging.debug(f'⏰ RUN {self_name}... ⏰')
        while True:
            sync_products_interval = 7200
            try:
                sync_products_interval = int(await preferences.get('sync_products_interval'))
            except Exception as e:
                logging.error(e)
            logging.debug(f'⌛♾ {self_name} {sync_products_interval} SECONDS WAIT... ♾⌛')
            sleep(sync_products_interval)
            ############################
            if page.sync_products_running:
                logging.debug(f'⌛♾ {self_name} SYNC PRODUCTS IS RUNNING NOW, WAIT NEXT TIME INTERVAL ♾⌛')
            else:
                logging.debug(f'⌛♾⏰ {self_name} RUN SYNC PRODUCTS... ⏰♾⌛')
                await sync_products(page)
                logging.debug(f'⌛♾ {self_name} SYNC PRODUCTS FINISHED ♾⌛')
            ############################
            if page.sync_customers_running:
                logging.debug(f'⌛♾ {self_name} SYNC CUSTOMERS IS RUNNING NOW, WAIT NEXT TIME INTERVAL ♾⌛')
            else:
                logging.debug(f'⌛♾⏰ {self_name} RUN SYNC CUSTOMERS... ⏰♾⌛')
                await sync_customers(page)
                logging.debug(f'⌛♾ {self_name} SYNC CUSTOMERS FINISHED ♾⌛')
    page.run_thread(infinity_sync_cache)

    async def infinity_sync_sales():
        self_name = f'{current_thread().name}.{inspect.stack()[0][3]}'
        logging.debug(f'⌛⏰ RUN {self_name}... ⏰⌛')
        while True:
            sync_sales_interval = 300
            logging.debug(f'⌛📂📄🖊️ {self_name} DEFAULT {sync_sales_interval} SECONDS WAIT... 🖊️📄📂⌛')
            if not await preferences.contains_key('sync_sales_interval'):
                await preferences.set('sync_sales_interval', sync_sales_interval)
                logging.debug(f'⌛📷♾ {self_name} SET {sync_sales_interval} SECONDS WAIT... ♾📷⌛')
            else:
                syncsalesinterval = await preferences.get('sync_sales_interval')
                logging.debug(f'⌛📷♾ {self_name} GET {syncsalesinterval} SECONDS WAIT... ♾📷⌛')
                try:
                    sync_sales_interval = int(syncsalesinterval)
                except ValueError as e:
                    sync_sales_interval = int(syncsalesinterval.replace('"', ''))
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

    async def close_autocomplete(evt):
        await page.bar_search_products.close_view()

    def on_search(evt: flet.ControlEvent):
        if evt.control.value:
            product_add(evt.control.value)
            evt.control.value = ''
            evt.control.update()
            evt.control.focus()

    search_lv = flet.ListView()

    async def search_close_autocompletes(value: str = '', only_clear: bool = False):
        if search_lv.controls:
            search_lv.controls = []
            if not only_clear:
                await page.bar_search_products.close_view()
            if value:
                page.bar_search_products.value = value
            update_status_ctrl({4:'💬'})
            page.bar_search_products.update()

    async def on_search_change(evt):
        if len(evt.data) < (await preferences.get('search_auto_min_count') or 2):
            search_close_autocompletes(evt.data)
        else:
            products, msg = page.db_conn.search_products(evt.data, limit_expression=f' LIMIT {await preferences.get('search_auto_limit') or 1000}')
            if products:
                update_status_ctrl({4:f'💬{len(products)}'})
                search_lv.controls = [flet.ListTile(title=flet.Text(product['name']), on_click=lambda evt: basket_add_product(evt.control.data), data=product) for product in products]
                page.bar_search_products.open_view()
                page.bar_search_products.update()
            else:
                search_close_autocompletes(evt.data, True)

    page.is_search_bar_focused = True
    def on_focus_search_bar(evt):
        page.is_search_bar_focused = True

    page.bar_search_products = flet.SearchBar(bar_hint_text='Search products...',
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

    page.basket = BasketControl(
        expand_icon_color = flet.Colors.GREEN,
        elevation = 4,
        divider_color=flet.Colors.GREEN,
        spacing = 0
    )

    page.customer_dialog = CustomerDialog(modal=True)
    page.add(page.customer_dialog)

    async def basket_order_customer(evt: flet.ControlEvent = None):
        if await preferences.get('use_order_customer_dialog'):
            if page.customer_dialog.doc_type != 'order_customer':
                page.customer_dialog.doc_type = 'order_customer'
            if not page.customer_dialog.open:
                page.show_dialog(page.customer_dialog)
        else:
            if len(page.basket.controls):
                page.run_thread(page.basket.send_data, 'order_customer')

    async def basket_sale(evt: flet.ControlEvent = None):
        if await preferences.get('use_sale_customer_dialog'):
            if page.customer_dialog.doc_type != 'sale':
                page.customer_dialog.doc_type = 'sale'
            if not page.customer_dialog.open:
                page.show_dialog(page.customer_dialog)
        else:
            if len(page.basket.controls):
                page.run_thread(page.basket.send_data)

    def basket_order(evt: flet.ControlEvent = None):
        if page.customer_dialog:
            if page.customer_dialog.open:
                page.pop_dialog()
            page.customer_dialog.open = False
        if len(page.basket.controls):
            page.run_thread(page.basket.send_data, 'order')

    async def basket_add_product(product: dict):
        headers, prod = page.http_conn.get_product(product['id'], network_timeout=await preferences.get('network_timeout_get_product') or .1)
        product['count'] = '-' if not prod else prod['count']
        await page.basket.add(product)
        search_close_autocompletes()

    def product_search(code: str):
        logging.info(['CODE', code])
        prods, msg = page.db_conn.search_products(code)
        logging.info(['FOUND', prods, msg])
        return prods

    def product_add(code: str):
        page.add(flet.CupertinoActivityIndicator(radius=50, color=flet.Colors.RED, animating=True))
        products = product_search(code)
        if len(products) == 1:
            basket_add_product(products[0])
        elif products:
            logging.debug(f'{code} FOUND MANY')
            alert(code, 'FOUND MANY, PLEASE SELECT ONE')
        else:
            logging.debug(f'{code} NOT FOUND')
            alert(code, 'NOT FOUND')

    def on_click_pagelet(evt: flet.ControlEvent):
        logging.debug(f'ON_CLICK_PAGELET {evt.control.parent}')
        pagelet.appbar = None
        pagelet.end_drawer.open = True
        pagelet.end_drawer.update()
        page.update()

    page.products_dialog = None
    def open_poducts(evt: flet.ControlEvent):
        if not page.products_dialog:
            page.products_dialog = ProductsDialog(modal=True, db_conn=page.db_conn)
            page.add(page.products_dialog)
        page.show_dialog(page.products_dialog)

    page.documents_dialog = None
    def open_documents(evt: flet.ControlEvent):
        if not page.documents_dialog:
            page.documents_dialog = DocumentsDialog(modal=True, http_conn=page.http_conn)
            page.add(page.documents_dialog)
        page.show_dialog(page.documents_dialog)

    def basket_clear(evt: flet.ControlEvent):
        page.basket.clearing()

    bottomappbar_content = flet.Row(
        controls=[
            flet.IconButton(icon_size=20, icon=flet.Icons.MENU, icon_color=flet.Colors.WHITE, on_click=on_click_pagelet),
            flet.Container(page.status_ctrl, expand=True),
            flet.IconButton(icon_size=20, icon=flet.Icons.PRINT, icon_color=flet.Colors.WHITE, on_click=open_documents),
            flet.IconButton(icon_size=20, icon=flet.Icons.ADD, on_click=open_poducts),
            flet.IconButton(icon_size=20, icon=flet.Icons.DELETE, on_click=basket_clear)
        ]
    )

    bottomappbar = flet.BottomAppBar(bottomappbar_content, bgcolor=flet.Colors.GREEN)#, shape=flet.NotchShape.CIRCULAR)

    content_panel = flet.ListView(controls=[page.basket])

    logging.debug(f'w={page.window.width:.2f}; h={page.window.height:.2f}; {page.client_ip}; {page.client_user_agent}; {page.pwa}')

    def handle_dismiss_navigation_drawer(evt: flet.ControlEvent):
        logging.debug(f'DISMISS {evt.control}')
        pagelet.appbar = topbar
        page.update()

    async def handle_change_navigation_drawer(evt: flet.ControlEvent):
        logging.debug(f'CHANGED {evt.control.selected_index}')
        if evt.control.selected_index == 0:
            basket_order()
        elif evt.control.selected_index == 1:
            page.settings_dialog = SettingsDialog()
            page.show_dialog(page.settings_dialog)
        elif evt.control.selected_index == 2:
            #page.products_dialog = ProductsDialog()
            page.show_dialog(page.products_dialog)
        elif evt.control.selected_index == 3:
            if not page.sync_products_running:
                cnt, msg = page.db_conn.clear_products()
                logging.debug([msg, cnt])
                page.run_thread(sync_products, page)
                #cnt, msg = page.db_conn.clear_customers()
                #logging.debug([msg, cnt])
        elif evt.control.selected_index == 4:
            page.about_dialog = AboutDialog()
            page.show_dialog(page.about_dialog)
        elif evt.control.selected_index == 5:
            await preferences.set('user', {})
            if page.platform == 'android':
                import os
                os._exit(0)
            else:
                page.window.close()
        pagelet.end_drawer.open = False
        pagelet.end_drawer.update()

    #topbar = flet.CupertinoAppBar(
    topbar = flet.AppBar(
        #leading=flet.Icon(flet.icons.WB_SUNNY),
        #trailing=flet.Icon(flet.icons.WB_SUNNY_OUTLINED),
        #title=flet.SearchBar(bar_hint_text="Search ...", on_submit=on_search),
        title=flet.Row([
            page.bar_search_products,
            #flet.IconButton(icon=flet.Icons.LOCAL_SHIPPING, on_click=basket_order),
            flet.IconButton(icon=flet.Icons.SHOPPING_BASKET, on_click=basket_order_customer),
            page.basket.sum_final,
            flet.IconButton(icon=flet.Icons.POINT_OF_SALE, on_click=basket_sale)
            ]),
        bgcolor=flet.Colors.GREEN_100)

    pagelet = flet.Pagelet(
        appbar=topbar,
        content=content_panel,
        bgcolor=flet.Colors.WHITE,
        bottom_appbar=bottomappbar,
        end_drawer=flet.NavigationDrawer(
            on_dismiss=handle_dismiss_navigation_drawer,
            on_change=handle_change_navigation_drawer,
            controls=[
                flet.NavigationDrawerDestination(icon=flet.Icons.LOCAL_SHIPPING, label='🚚'),
                flet.NavigationDrawerDestination(icon=flet.Icons.ADD_TO_HOME_SCREEN_SHARP, label='🏠'),
                flet.NavigationDrawerDestination(icon=flet.Icons.ADD_COMMENT, label='➕'),
                flet.NavigationDrawerDestination(icon=flet.Icons.LOCK_RESET, label='🔄'),
                flet.NavigationDrawerDestination(icon=flet.Icons.ROUNDABOUT_LEFT, label='ℹ'),
                flet.NavigationDrawerDestination(icon=flet.Icons.EXIT_TO_APP, label='🔚'),
            ],
        ),
        floating_action_button=flet.FloatingActionButton('SCAN', on_click=scan_barcode),
        floating_action_button_location=flet.FloatingActionButtonLocation.CENTER_DOCKED,
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

    def on_custom_keyboard(evt: flet.KeyboardEvent):
        match evt.key:
            case 'Escape':
                if alert_dlg.open:
                    page.pop_dialog()
                    alert_dlg.open = False
                if page.customer_dialog:
                    page.customer_dialog = None
            case 'Enter':
                if page.customer_dialog and page.customer_dialog.open:
                    page.customer_dialog.send_data()
                    page.pop_dialog()
                    page.customer_dialog.open = False
            case 'Delete':
                if evt.ctrl:
                    page.basket.clearing()
            case 'F1':
                page.about_dialog = AboutDialog()
                page.show_dialog(page.about_dialog)
            case 'F2':
                if evt.ctrl:
                    del page.basket.customer
                    page.update_status_ctrl({5:f'👨{page.basket.customer}'})
                    if page.customer_dialog and page.customer_dialog.open:
                        page.pop_dialog()
                        page.customer_dialog.open = False
                else:
                    if page.customer_dialog and not page.customer_dialog.open:
                        page.show_dialog(page.customer_dialog)
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
    page.on_keyboard_event = on_custom_keyboard

    page.locale_configuration = flet.LocaleConfiguration([flet.Locale(language_code='en', country_code='US'), flet.Locale(language_code='ru', country_code='RU')])


#flet.run(main, port=8550, view=flet.AppView.WEB_BROWSER)
flet.run(main)
