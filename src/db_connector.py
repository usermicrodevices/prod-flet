import logging, sqlite3, sys


sqlite3.register_adapter(list, lambda args: f'{args}')
sqlite3.register_converter('list_args', lambda arg: eval(arg))

sqlite3.register_adapter(dict, lambda kwargs: f'{kwargs}')
sqlite3.register_converter('kwargs', lambda kwarg: eval(kwarg))


class DbConnector():

    def __init__(self, *args, **kwargs):
        self.conn = sqlite3.connect(kwargs.get('file_name', 'prod.db'), autocommit=True, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cur = self.conn.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS products(id UNIQUE PRIMARY KEY, name TEXT, article TEXT, barcodes TEXT, qrcodes TEXT, cost REAL, price REAL, currency BLOB, unit BLOB, grp BLOB);')
        self.cur.execute('CREATE TABLE IF NOT EXISTS records(doc_type TEXT DEFAULT "sale", registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, product INTEGER, count REAL, cost REAL DEFAULT 0.0, price REAL, sum_final REAL, currency BLOB);')

    def __del__(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def product_as_dict(self, v):
        logging.debug(['PRODUCT_AS_DICT', v])
        return {'id':v[0],
            'name':v[1],
            'article':v[2],
            'barcodes':eval(v[3]) if v[3] else [],
            'qrcodes':eval(v[4]) if v[4] else [],
            'cost':v[5],
            'price':v[6],
            'currency':eval(v[7]) if v[7] else {},
            'unit':eval(v[8]) if v[8] else {},
            'grp':eval(v[9]) if v[9] else {}
        }

    def record_as_dict(self, v):
        return {'id':v[0], 'doc_type':v[1], 'registered_at':v[2], 'product':v[3], 'count':v[4], 'cost':v[5], 'price':v[6], 'sum_final':v[7], 'currency':eval(v[8]) if v[8] else {}}

    def update_products(self, *args, **kwargs):
        if not self.cur:
            return False, f'CURSOR INVALID {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        if 'data' in kwargs:
            try:
                self.cur.executemany('INSERT INTO products VALUES(:id, :name, :article, :barcodes, :qrcodes, :cost, :price, :currency, :unit, :grp)', kwargs.get('data', []))
            except sqlite3.IntegrityError as e:
                updated = 0
                for v in kwargs.get('data', []):
                    try:
                        self.cur.execute(f'''UPDATE products SET name='{v["name"]}', article='{v["article"]}', barcodes="{v['barcodes']}", qrcodes="{v['qrcodes']}", cost='{v["cost"]}', price='{v["price"]}', currency='{v["currency"]}', unit='{v["unit"]}', grp="{v['grp']}" WHERE id={v['id']};''')
                    except Exception as e:
                        logging.debug([e, f'{v}'])
                    else:
                        updated += 1
                logging.debug(['UPDATED PRODUCTS', updated])
            except Exception as e:
                return False, f'{e} {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
            #self.conn.commit()
        return True, f'SUCCESS {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'

    def get_product(self, *args, **kwargs):
        if not self.cur:
            return None, f'CURSOR INVALID {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        if not len(args):
            return None, f'EMPTY SEARCH STRING {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        result = None
        s = args[0]
        if not isinstance(s, (int, float)) and not s:
            return None, f'EMPTY SEARCH STRING [{s}] {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        where_exp = f'''WHERE name LIKE ('%{s}%') OR article='{s}' OR barcodes LIKE ('%{s}%') OR qrcodes LIKE ('%{s}%')'''
        if s.isdigit():
            where_exp += f''' OR id={s}'''
        search_sql = f'''SELECT * FROM products {where_exp} LIMIT 1;'''
        try:
            res = self.cur.execute(search_sql)
        except Exception as e:
            return None, f'{search_sql} {e} {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        else:
            v = res.fetchone()
            if v:
                result = self.product_as_dict(v)
        return result, f'SUCCESS {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'

    def get_products(self, *args, **kwargs):
        if not self.cur:
            return None, f'CURSOR INVALID {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        limit, offset = kwargs.get('limit', 10), kwargs.get('offset', 0)
        res = self.cur.execute(f'SELECT * FROM products LIMIT {limit} OFFSET {offset};')
        result = None
        if res:
            result = [self.product_as_dict(v) for v in res.fetchall()]
        logging.debug(result)
        return result, f'SUCCESS {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'

    def insert_records(self, data):
        if not self.cur:
            return False, f'CURSOR INVALID {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        if not data:
            return False, f'EMPTY DATA {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        else:
            try:
                self.cur.executemany('INSERT INTO records VALUES(:doc_type, :registered_at, :product, :count, :cost, :price, :sum_final, :currency)', data)
            except Exception as e:
                return False, f'{e} {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        return True, f'SUCCESS {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'

    def get_grouped_records(self, *args, **kwargs):
        if not self.cur:
            return None, f'CURSOR INVALID {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        regs = self.cur.execute('SELECT registered_at FROM records GROUP BY registered_at ORDER BY registered_at;')
        if regs:
            result = []
            for reg in regs:
                sql_query = f'SELECT * FROM records WHERE registered_at={reg};'
                logging.debug(sql_query)
                res = self.cur.execute(sql_query)
                if res:
                    result.append([self.record_as_dict(v) for v in res.fetchall()])
            logging.debug(result)
            return result, f'SUCCESS {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        return None, f'EMPTY RECORDS {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'

    def clear_records(self, ids: list):
        if not self.cur:
            return None, f'CURSOR INVALID {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
        sql_query = f'DELETE FROM records WHERE rowid IN {tuple(ids)};'
        logging.debug(sql_query)
        self.cur.execute(sql_query)
        return self.cur.rowcount, f'FINISHED {self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
