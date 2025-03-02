import asyncio, flet, json, logging, requests, sys
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
        self.url_product = f'{self.url_base}/api/product/'
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

    def auth(self, show_alert=False):
        self.auth_succes = False
        logging.debug(['🍪GET🍪', self.url_admin])
        try:
            response = self.session.get(self.url_admin)
        except Exception as e:
            logging.error(f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} {e}')
            if show_alert:
                self.alert(f'{e}', self.url_admin)
            return 500
        parser = CSRFParser()
        parser.feed(response.content.decode('utf-8'))
        if parser.csrfmiddlewaretoken:
            payload = f'{{"username":"{self.http_login}", "password":"{self.http_password}"}}'
            headers = {'content-type':'application/json', 'X-CSRFToken':parser.csrfmiddlewaretoken}
            self.session.headers.update(headers)
            logging.debug(['🍰POST🍰', self.url_loign, payload])
            try:
                response = self.session.post(self.url_loign, data=payload)
            except Exception as e:
                logging.error(f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} {e}')
                return 500
            else:
                logging.debug(['🍰RESPONSE🍰', response.status_code])
                logging.debug(['🍰SESSION.COOKIES🍰', self.session.cookies])
                if response.status_code == 200:
                    self.auth_succes = True
                    self.session.headers['X-CSRFToken'] = self.session.cookies.get('csrftoken', parser.csrfmiddlewaretoken)
                    return 200
        else:
            if show_alert:
                self.alert(self.url_admin, 'error authorization')
        return 400

    def get_products_cash(self, prod_page=1, limit=100):
        data = []
        url_args = f'{self.url_products_cash}?limit={limit}&page={prod_page}'
        logging.debug(['🎂GET🎂', url_args])
        try:
            response = self.session.get(url_args)
        except Exception as e:
            logging.error(f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} {e}')
            return {}, data
        logging.debug(['🎂RESPONSE🎂', response.status_code])
        logging.debug(['🎂RESPONSE.HEADERS🎂', response.headers])
        logging.debug(['🎂SESSION.COOKIES🎂', self.session.cookies])
        logging.debug(['🎂SESSION.HEADERS🎂', self.session.headers])
        if response.status_code == 200:
            data = eval(json.loads(response.content))
        else:
            logging.warning(['🎂RESPONSE.CONTENT🎂', json.loads(response.content)])
        logging.debug(['🎂PRODUCTS.LENGTH🎂', len(data)])
        return response.headers, data

    def get_product(self, prod_id=1):
        data = {}
        url_args = f'{self.url_product}{prod_id}/'
        logging.debug(['🎂GET🎂', url_args])
        try:
            response = self.session.get(url_args)
        except Exception as e:
            logging.error(f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} {e}')
            return {}, data
        logging.debug(['🎂RESPONSE🎂', response.status_code])
        logging.debug(['🎂RESPONSE.HEADERS🎂', response.headers])
        logging.debug(['🎂SESSION.COOKIES🎂', self.session.cookies])
        logging.debug(['🎂SESSION.HEADERS🎂', self.session.headers])
        if response.status_code == 200:
            res = eval(json.loads(response.content).replace('null', 'None'))
            if len(res):
                data = res[0]['fields']
                data['id'] = res[0]['pk']
                data['count'] = response.headers.get('count', 0)
        else:
            logging.warning(['🎂RESPONSE.CONTENT🎂', json.loads(response.content)])
        logging.debug(['🎂PRODUCTS.LENGTH🎂', len(data)])
        return response.headers, data

    def post_doc_cash(self, data):
        json_data = json.dumps(data)
        logging.debug(['🎂POST🎂', self.url_doc_cash, json_data])
        try:
            response = self.session.post(self.url_doc_cash, json_data)
        except Exception as e:
            logging.error(f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} {e}')
            return False
        logging.debug(['🎂RESPONSE🎂', response.status_code])
        logging.debug(['🎂SESSION.COOKIES🎂', self.session.cookies])
        logging.debug(['🎂SESSION.HEADERS🎂', self.session.headers])
        logging.debug(['🎂RESPONSE.CONTENT🎂', response.content])
        if response.status_code != 200:
            return False
        res = eval(response.content.decode('utf8') if response.content else {})
        logging.debug(['🎂RESPONSE.CONTENT🎂', res])
        return True if res.get('result', 'error') == 'success' else False
