import sys
from subprocess import Popen, PIPE, STDOUT
#from pypdf import PdfWriter
import flet as ft
from log_tools import *


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


class DocumentsDialog(ft.AlertDialog):
    def __init__(self, *args, **kwargs):
        page = kwargs.pop('page')
        super().__init__(*args, **kwargs)
        self.limit = 10
        self.offset = 0
        self.pages, documents, msg = page.http_conn.get_documents()
        if not documents:
            self.content = ft.Text(msg)
        else:
            captions = [
                Caption(title='id', numeric=True),
                Caption(title='data'),
                Caption(title='people'),
                Caption(title='sum', numeric=True)
            ]
            self.data_table = ft.DataTable(
                show_checkbox_column = True,
                column_spacing = 5,
                border_radius = 5,
                border = ft.border.all(2, 'green'),
                vertical_lines = ft.BorderSide(2, 'green'),
                horizontal_lines = ft.BorderSide(2, 'green'),
                columns = captions,
                rows = self.data_as_rows(documents)
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

    def log(self, lvl=LN, msgs=[], *args, **kwargs):
        s = f'{LICONS[lvl]}::{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        for m in msgs:
            s += f'::{m}'
            if hasattr(m, '__traceback__'):
                s += f'🇱🇮🇳🇪{m.__traceback__.tb_lineno}'
        logging.log(lvl, s, *args, **kwargs)

    def data_as_rows(self, data):
        return [ft.DataRow(cells=[ft.DataCell(ft.Text(d['pk'])), ft.DataCell(ft.Text(d['fields']['registered_at'])), ft.DataCell(ft.Text(d['fields']['customer'])), ft.DataCell(ft.Text(d['fields']['sum_final']))], on_select_changed=self.on_select, data=d) for d in data]

    def on_select(self, evt):
        self.log(LD, ['ON_SELECT', evt.data, evt.control.data])
        if evt.control.data:
            doc_id = evt.control.data['pk']
            printer_content, msg = self.page.http_conn.get_sales_receipt(doc_id)
            self.log(LD, [msg, printer_content])
            if printer_content:
                #pdf = PdfWriter()
                #pdf.add_attachment(f'sales_receipt_{doc_id}.pdf', html_content.decode('utf-8'))
                #pdf.write_stream(lp.stdin)
                #pdf.write('/dev/lpr')
                lp = Popen(['lpr'], stdin=PIPE, stdout=PIPE, stderr=STDOUT)#, encoding='utf-8')
                #res = lp.stdin.write(printer_content.decode('utf-8'))
                res = lp.communicate(input=printer_content)
                self.log(LD, ['LPR RESULT', res])
        self.page.close(self)

    def handle_action_click(self, evt):
        if evt.control.is_ok:
            self.page.get_sales_receipt()
        self.page.close(evt.control.parent)

    def handle_prev(self, evt):
        self.pages, documents, msg = self.page.http_conn.get_documents(self.offset, self.limit)
        if self.offset >= self.pages or self.offset > 0:
            self.offset = 0 if self.offset < 0 else self.offset - 1
            if documents:
                self.data_table.rows = self.data_as_rows(documents)
                self.data_table.update()

    def handle_next(self, evt):
        self.pages, documents, msg = self.page.http_conn.get_documents(self.offset, self.limit)
        if self.offset < self.pages:
            self.offset += 1
            if documents:
                self.data_table.rows = self.data_as_rows(documents)
                self.data_table.update()
