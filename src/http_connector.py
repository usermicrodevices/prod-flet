import asyncio, flet, json, logging, requests
#import requests_async as requests

from html.parser import HTMLParser


class CSRFParser(HTMLParser):
    csrfmiddlewaretoken = ''
    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            kwargs = dict(attrs)
            if set(['type', 'name', 'value']) <= set(kwargs.keys()) and kwargs['name'] == 'csrfmiddlewaretoken':
                self.csrfmiddlewaretoken = kwargs['value']


class HttpConnector():
    session = requests.Session()
    auth_succes = False

    def __init__(self, page: flet.Page):
        self.http_protocol = page.client_storage.get('protocol') or 'http://'
        self.http_host = page.client_storage.get('host')
        self.http_port = page.client_storage.get('port')
        self.http_login = page.client_storage.get('login')
        self.http_password = page.client_storage.get('password')
        self.url_base = f'''{self.http_protocol}{self.http_host}{f':{self.http_port}' if self.http_port else ''}'''
        self.url_admin = f'{self.url_base}/admin/login/'
        self.url_loign = f'{self.url_base}/api/login/'
        self.url_products_cash = f'{self.url_base}/api/products/cash/'
        self.url_doc_cash = f'{self.url_base}/api/doc/cash/'
        self.page = page

    async def __aenter__(self):
        while not self.page:
            await asyncio.sleep(1)

    async def __aexit__(self, exc_type, exc, tb):
        while not self.page:
            await asyncio.sleep(1)

    def alert(self, msg: str, caption: str = 'error'):
        self.page.open(flet.AlertDialog(modal=True, title=flet.Text(caption), content=flet.Text(msg), actions=[flet.TextButton('ok', on_click=lambda e: self.page.close(e.control.parent))]))

    def auth(self):
        self.auth_succes = False
        logging.debug(['🍪GET🍪', self.url_admin])
        try:
            response = self.session.get(self.url_admin)
        except Exception as e:
            logging.error([e])
            self.alert(f'{e}', self.url_admin)
            return 500
        parser = CSRFParser()
        parser.feed(response.content.decode('utf-8'))
        if parser.csrfmiddlewaretoken:
            payload = f'{{"username":"{self.http_login}", "password":"{self.http_password}"}}'
            headers = {'content-type':'application/json', 'X-CSRFToken':parser.csrfmiddlewaretoken}
            self.session.headers.update(headers)
            logging.debug(['🍰POST🍰', self.url_loign, payload])
            response = self.session.post(self.url_loign, data=payload)
            logging.debug(['🍰RESPONSE🍰', response.status_code])
            logging.debug(['🍰SESSION.COOKIES🍰', self.session.cookies])
            if response.status_code == 200:
                self.auth_succes = True
        else:
            self.alert(self.url_admin, 'error authorization')

    def get_products_cash(self):
        logging.debug(['🎂GET🎂', self.url_products_cash])
        response = self.session.get(self.url_products_cash)
        logging.debug(['🎂RESPONSE🎂', response.status_code])
        logging.debug(['🎂SESSION.COOKIES🎂', self.session.cookies])
        logging.debug(['🎂SESSION.HEADERS🎂', self.session.headers])
        data = eval(json.loads(response.content))
        logging.debug(['🎂PRODUCTS.LENGTH🎂', len(data)])
        return data

    def post_doc_cash(self, data):
        json_data = json.dumps(data)
        logging.debug(['🎂POST🎂', self.url_doc_cash, json_data])
        response = self.session.post(self.url_doc_cash, json_data)
        logging.debug(['🎂RESPONSE🎂', response.status_code])
        logging.debug(['🎂SESSION.COOKIES🎂', self.session.cookies])
        logging.debug(['🎂SESSION.HEADERS🎂', self.session.headers])
        logging.debug(['🎂RESPONSE.CONTENT🎂', response.content])
        if response.status_code != 200:
            return False
        res = eval(response.content.decode('utf8') if response.content else {})
        logging.debug(['🎂RESPONSE.CONTENT🎂', res])
        return True if res.get('result', 'error') == 'success' else False
