import asyncio, flet, json, requests, sys

from html.parser import HTMLParser

from log_tools import *


preferences = flet.SharedPreferences()


class CSRFParser(HTMLParser):
    csrfmiddlewaretoken = ''
    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            kwargs = dict(attrs)
            if set(['type', 'name', 'value']) <= set(kwargs.keys()) and kwargs['name'] == 'csrfmiddlewaretoken':
                self.csrfmiddlewaretoken = kwargs['value']


class HttpConnector():
    session = requests.Session()
    auth_success = False

    async def __init__(self, page: flet.Page):
        self.http_protocol = await preferences.get('protocol') or 'http://'
        self.http_host = await preferences.get('host')
        self.http_port = await preferences.get('port')
        self.http_login = await preferences.get('login')
        self.http_password = await preferences.get('password')
        self.url_base = f'''{self.http_protocol}{self.http_host}{f':{self.http_port}' if self.http_port else ''}'''
        self.url_admin = f'{self.url_base}/admin/login/'
        self.url_loign = f'{self.url_base}/api/login/'
        self.url_product = f'{self.url_base}/api/product/'
        self.url_products_cash = f'{self.url_base}/api/products/cash/'
        self.url_doc_cash = f'{self.url_base}/api/doc/cash/'
        self.url_documents = f'{self.url_base}/api/docs/'
        self.url_sales_receipt = f'{self.url_base}/api/doc/%s/sales_receipt%s'
        self.url_customers = f'{self.url_base}/api/customers/'
        self.page = page

    def __aenter__(self):
        while not self.page:
            asyncio.sleep(1)

    async def __aexit__(self, exc_type, exc, tb):
        while not self.page:
            await asyncio.sleep(1)

    @property
    def method_name(self):
        return f'{__name__}.{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'

    def log(self, lvl=LN, msgs=[], *args, **kwargs):
        s = f'{LICONS[lvl]}::{__name__}.{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        for m in msgs:
            s += f'::{m}'
            if hasattr(m, '__traceback__'):
                s += f'🇱🇮🇳🇪{m.__traceback__.tb_lineno}'
        logging.log(lvl, s, *args, **kwargs)

    def alert(self, msg: str, caption: str = 'error'):
        self.page.alert(msg, caption)

    async def auth(self, show_alert=False, network_timeout=10):
        self.auth_success = False
        await preferences.set('user', {})
        self.log(LD, ['🍪GET🍪', self.url_admin])
        try:
            response = self.session.get(self.url_admin, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return 400
        except Exception as e:
            self.log(LE, [e])
            if show_alert:
                self.alert(f'{e}', self.url_admin)
            return 500
        parser = CSRFParser()
        parser.feed(response.content.decode('utf-8'))
        if parser.csrfmiddlewaretoken:
            payload = f'{{"username":"{self.http_login}", "password":"{self.http_password}"}}'
            headers = {'content-type':'application/json', 'X-CSRFToken':parser.csrfmiddlewaretoken}
            self.session.headers.update(headers)
            self.log(LD, ['🍰POST🍰', self.url_loign, payload])
            try:
                response = self.session.post(self.url_loign, data=payload, timeout=network_timeout)
            except requests.exceptions.ConnectTimeout as e:
                self.log(LW, [e])
                return 400
            except Exception as e:
                self.log(LE, [e])
                return 500
            else:
                self.log(LD, ['🍰RESPONSE🍰', response.status_code])
                self.log(LD, ['🍰SESSION.COOKIES🍰', self.session.cookies])
                if response.status_code == 200:
                    self.auth_success = True
                    self.session.headers['X-CSRFToken'] = self.session.cookies.get('csrftoken', parser.csrfmiddlewaretoken)
                    user_data = {}
                    try:#data = response.json()
                        data = json.loads(response.content.decode('utf-8').replace('"True"', 'true').replace('"False"', 'false').replace('"None"', 'null'))
                    except Exception as e:
                        self.log(LE, [e])
                    else:
                        user_data = data.get('user', {})
                        await preferences.set('user', user_data)
                    self.log(LD, ['🍰RESPONSE.CONTENT🍰', user_data])
                    return 200
        else:
            if show_alert:
                self.alert(self.url_admin, 'error authorization')
        return 400

    def get_products_cash(self, id_page=1, limit=100, network_timeout=10):
        data = []
        url_args = f'{self.url_products_cash}?limit={limit}&page={id_page}'
        self.log(LD, ['🎂GET🎂', url_args])
        try:
            response = self.session.get(url_args, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return {}, data
        except Exception as e:
            self.log(LE, [e])
            return {}, data
        self.log(LD, ['🎂RESPONSE🎂', response.status_code])
        self.log(LD, ['🎂RESPONSE.HEADERS🎂', response.headers])
        self.log(LD, ['🎂SESSION.COOKIES🎂', self.session.cookies])
        self.log(LD, ['🎂SESSION.HEADERS🎂', self.session.headers])
        if response.status_code == 200:
            data = eval(json.loads(response.content))
        else:
            self.log(LW, ['🎂RESPONSE.CONTENT🎂', json.loads(response.content)])
        self.log(LD, ['🎂PRODUCTS.LENGTH🎂', len(data)])
        return response.headers, data

    def get_product(self, prod_id=1, network_timeout=10):
        data = {}
        url_args = f'{self.url_product}{prod_id}/'
        self.log(LD, ['🎂GET🎂', url_args])
        try:
            response = self.session.get(url_args, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return {}, data
        except Exception as e:
            self.log(LE, [e])
            return {}, data
        self.log(LD, ['🎂RESPONSE🎂', response.status_code])
        self.log(LD, ['🎂RESPONSE.HEADERS🎂', response.headers])
        self.log(LD, ['🎂SESSION.COOKIES🎂', self.session.cookies])
        self.log(LD, ['🎂SESSION.HEADERS🎂', self.session.headers])
        if response.status_code == 200:
            if not response.content:
                return {}, data
            res = eval(json.loads(response.content).replace('null', 'None'))
            if len(res):
                data = res[0]['fields']
                data['id'] = res[0]['pk']
                data['count'] = response.headers.get('count', 0)
        else:
            self.log(LW, ['🎂RESPONSE.CONTENT🎂', json.loads(response.content)])
        self.log(LD, ['🎂PRODUCTS.LENGTH🎂', len(data)])
        return response.headers, data

    def post_doc_cash(self, data, network_timeout=10):
        json_data = json.dumps(data)
        self.log(LD, ['🎂POST🎂', self.url_doc_cash, json_data])
        try:
            response = self.session.post(self.url_doc_cash, json_data, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return False
        except Exception as e:
            self.log(LE, [e])
            return False
        self.log(LD, ['🎂RESPONSE🎂', response.status_code])
        self.log(LD, ['🎂SESSION.COOKIES🎂', self.session.cookies])
        self.log(LD, ['🎂SESSION.HEADERS🎂', self.session.headers])
        self.log(LD, ['🎂RESPONSE.CONTENT🎂', response.content])
        if response.status_code != 200:
            return False
        res = eval(response.content.decode('utf8') if response.content else {})
        self.log(LD, ['🎂RESPONSE.CONTENT🎂', res])
        return True if res.get('result', 'error') == 'success' else False

    def get_documents(self, id_page=0, limit=10, doctype='sale', network_timeout=10):
        url_args = f'{self.url_documents}?limit={limit}'
        if id_page > 0:
            url_args += f'&page={id_page}'
        url_args += f'&type__alias={doctype}'
        self.log(LD, ['🎂GET🎂', url_args])
        try:
            response = self.session.get(url_args, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return 0, [], f'{e}'
        except Exception as e:
            self.log(LE, [e])
            return 0, [], f'{e}'
        self.log(LD, ['🎂RESPONSE🎂', response.status_code])
        self.log(LD, ['🎂RESPONSE.HEADERS🎂', response.headers])
        self.log(LD, ['🎂SESSION.COOKIES🎂', self.session.cookies])
        self.log(LD, ['🎂SESSION.HEADERS🎂', self.session.headers])
        msg = ''
        data = []
        if response.status_code == 200:
            data = eval(json.loads(response.content).replace('null', 'None'))
        else:
            msg = json.loads(response.content)
            self.log(LW, ['🎂RESPONSE.CONTENT🎂', msg])
        self.log(LD, ['🎂PRODUCTS.LENGTH🎂', len(data)])
        page_max = int(response.headers.get('page_max', 0))
        return page_max, data, msg

    def get_sales_receipt(self, id_doc=0, urlargs='?pdf=wkhtmltopdf', network_timeout=60):
        url_args = self.url_sales_receipt % (f'{id_doc}', urlargs)
        self.log(LD, ['🎂GET🎂', url_args])
        try:
            response = self.session.get(url_args, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return '', f'{e}'
        except Exception as e:
            self.log(LE, [e])
            return '', f'{e}'
        self.log(LD, ['🎂RESPONSE🎂', response.status_code])
        self.log(LD, ['🎂RESPONSE.HEADERS🎂', response.headers])
        self.log(LD, ['🎂SESSION.COOKIES🎂', self.session.cookies])
        self.log(LD, ['🎂SESSION.HEADERS🎂', self.session.headers])
        #return response.content.decode('utf8'), ''
        return response.content, ''

    def get_customers(self, id_page=1, limit=100, network_timeout=10):
        data = []
        url_args = f'{self.url_customers}?limit={limit}&page={id_page}'
        self.log(LD, ['🎂GET🎂', url_args])
        try:
            response = self.session.get(url_args, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return {}, data
        except Exception as e:
            self.log(LE, [e])
            return {}, data
        self.log(LD, ['🎂RESPONSE🎂', response.status_code])
        self.log(LD, ['🎂RESPONSE.HEADERS🎂', response.headers])
        self.log(LD, ['🎂SESSION.COOKIES🎂', self.session.cookies])
        self.log(LD, ['🎂SESSION.HEADERS🎂', self.session.headers])
        if response.status_code == 200:
            data = eval(json.loads(response.content))
        else:
            self.log(LW, ['🎂RESPONSE.CONTENT🎂', json.loads(response.content)])
        self.log(LD, ['🎂CUSTOMERS.LENGTH🎂', len(data)])
        return response.headers, data

    def post_customer(self, data, network_timeout=10):
        json_data = json.dumps(data)
        self.log(LD, ['🎂POST🎂', self.url_customers, json_data])
        try:
            response = self.session.post(self.url_customers, json_data, timeout=network_timeout)
        except requests.exceptions.ConnectTimeout as e:
            self.log(LW, [e])
            return False
        except Exception as e:
            self.log(LE, [e])
            return False
        self.log(LD, ['🎂RESPONSE🎂', response.status_code])
        self.log(LD, ['🎂SESSION.COOKIES🎂', self.session.cookies])
        self.log(LD, ['🎂SESSION.HEADERS🎂', self.session.headers])
        self.log(LD, ['🎂RESPONSE.CONTENT🎂', response.content])
        if response.status_code != 200:
            return False
        res = eval(response.content.decode('utf8') if response.content else {})
        self.log(LD, ['🎂RESPONSE.CONTENT🎂', res])
        return True if res.get('result', 'error') == 'success' else False
