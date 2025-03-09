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
        self.limit = 10
        self.offset = 0
        self.products_count, msg = page.db_conn.get_products_count()
        products, msg = page.db_conn.get_products(limit=10, offset=0)
        if not products:
            self.content = ft.Text(msg)
        else:
            captions = [
                Caption(title='id', numeric=True),
                Caption(title='article'),
                Caption(title='name'),
                Caption(title='price', numeric=True),
                Caption(title='barcodes')
            ]
            self.data_table = ft.DataTable(
                show_checkbox_column = True,
                column_spacing = 5,
                border_radius = 5,
                border = ft.border.all(2, 'green'),
                vertical_lines = ft.BorderSide(2, 'green'),
                horizontal_lines = ft.BorderSide(2, 'green'),
                columns = captions,
                rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(d['id'])), ft.DataCell(ft.Text(d['article'][:10])), ft.DataCell(ft.Text(d['name'][:10])), ft.DataCell(ft.Text(d['price'])), ft.DataCell(ft.Text('\n'.join(d['barcodes'])))], on_select_changed=self.on_select, data=d) for d in products]
            )
            self.content = ft.Column(controls=[
                ft.Row([self.data_table]),
                ft.Row([
                        ft.ElevatedButton('Prev', on_click=self.handle_prev),
                        ft.ElevatedButton('Next', on_click=self.handle_next)
                    ])
                ]
            )
        self.actions = [
            DialogAction('select', is_ok=True, on_click=self.handle_action_click),
            DialogAction('cancel', on_click=self.handle_action_click)
        ]
        self.page = page

    def on_select(self, evt):
        logging.debug(['ON_SELECT', evt.data, evt.control.data])
        if evt.control.data:
            self.page.basket.add(evt.control.data)
        self.page.close(self)

    def handle_action_click(self, evt):
        if evt.control.is_ok:
            self.page.sync_products()
        self.page.close(evt.control.parent)

    def handle_prev(self, evt):
        self.products_count, msg = self.page.db_conn.get_products_count()
        if self.offset >= self.products_count or self.offset > 0:
            self.offset -= self.limit
            if self.offset < 0:
                self.offset = 0
            products, msg = self.page.db_conn.get_products(limit=self.limit, offset=self.offset)
            if products:
                self.data_table.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(d['id'])), ft.DataCell(ft.Text(d['article'][:10])), ft.DataCell(ft.Text(d['name'][:10])), ft.DataCell(ft.Text(d['price'])), ft.DataCell(ft.Text('\n'.join(d['barcodes'])))], on_select_changed=self.on_select, data=d) for d in products]
                self.data_table.update()

    def handle_next(self, evt):
        self.products_count, msg = self.page.db_conn.get_products_count()
        if self.offset < self.products_count:
            self.offset += self.limit
            products, msg = self.page.db_conn.get_products(limit=self.limit, offset=self.offset)
            if products:
                self.data_table.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(d['id'])), ft.DataCell(ft.Text(d['article'][:10])), ft.DataCell(ft.Text(d['name'][:10])), ft.DataCell(ft.Text(d['price'])), ft.DataCell(ft.Text('\n'.join(d['barcodes'])))], on_select_changed=self.on_select, data=d) for d in products]
                self.data_table.update()
