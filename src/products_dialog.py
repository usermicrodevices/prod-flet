import flet as ft

import logging


class DialogAction(ft.TextButton):
    def __init__(self, *args, **kwargs):
        self.is_ok = kwargs.pop('is_ok', False)
        super().__init__(*args, **kwargs)


class CaptionRow(ft.Row):
    def __init__(self, *args, **kwargs):
        kwargs['alignment'] = ft.MainAxisAlignment.CENTER
        kwargs['controls'] = [ft.Text(kwargs.pop('title', ''), text_align=ft.TextAlign.CENTER)]
        super().__init__(*args, **kwargs)


class Caption(ft.DataColumn):
    def __init__(self, *args, **kwargs):
        kwargs['label'] = CaptionRow(title=kwargs.pop('title', ''))
        super().__init__(*args, **kwargs)


class ProductsDialog(ft.AlertDialog):
    def __init__(self, *args, **kwargs):
        page = kwargs.pop('page')
        super().__init__(*args, **kwargs)
        #self.title = ft.TextField('products')
        captions = [
            Caption(title='id', numeric=True),
            Caption(title='article'),
            Caption(title='name'),
            Caption(title='price', numeric=True),
            Caption(title='barcodes')
        ]
        products, msg = page.db_conn.get_products()
        if not products:
            self.content = ft.Text(msg)
        else:
            self.content = ft.DataTable(
                show_checkbox_column = True,
                column_spacing = 5,
                border_radius = 5,
                border = ft.border.all(2, 'green'),
                vertical_lines = ft.BorderSide(2, 'green'),
                horizontal_lines = ft.BorderSide(2, 'green'),
                columns = captions,
                rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(d['id'])), ft.DataCell(ft.Text(d['article'][:10])), ft.DataCell(ft.Text(d['name'][:10])), ft.DataCell(ft.Text(d['price'])), ft.DataCell(ft.Text('\n'.join(d['barcodes'])))], on_select_changed=self.on_select, data=d) for d in products]
            )
        self.actions = [
            DialogAction('select', is_ok=True, on_click=self.handle_action_click),
            DialogAction('cancel', on_click=self.handle_action_click)
        ]
        self.page = page

    def on_select(self, evt):
        logging.debug(['ON_SELECT', evt.data, evt.control.data])
        if evt.control.data:
            self.page.basket_add(evt.control.data)
        self.page.close(self)

    def handle_action_click(self, evt):
        if evt.control.is_ok:
            self.page.sync_products()
        self.page.close(evt.control.parent)
