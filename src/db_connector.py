import datetime, logging, sqlite3, sys

def adapt_date_iso(val):
    return val.isoformat()

def adapt_datetime_iso(val):
    return val.isoformat()

def adapt_datetime_epoch(val):
    return int(val.timestamp())

sqlite3.register_adapter(datetime.date, adapt_date_iso)
sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)
sqlite3.register_adapter(datetime.datetime, adapt_datetime_epoch)

def convert_date(val):
    return datetime.date.fromisoformat(val)

def convert_datetime(val):
    return datetime.datetime.fromisoformat(val)

def convert_timestamp(val):
    if not isinstance(val, int):
        try:
            val = int(val)
        except Exception as e:
            logging.error(['CONVERT_TIMESTAMP', val, e])
            return None
    return datetime.datetime.fromtimestamp(val).astimezone()

sqlite3.register_converter('date', convert_date)
sqlite3.register_converter('datetime', convert_datetime)
sqlite3.register_converter('timestamp', convert_timestamp)

sqlite3.register_adapter(list, lambda args: f'{args}')
sqlite3.register_converter('list_args', lambda arg: eval(arg))

sqlite3.register_adapter(dict, lambda kwargs: f'{kwargs}')
sqlite3.register_converter('kwargs', lambda kwarg: eval(kwarg))


class DbConnector():

    def __init__(self, *args, **kwargs):
        self.conn = sqlite3.connect(kwargs.get('file_name', 'prod.db'), autocommit=True, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        #self.conn.create_collation('UNOCASE', self.nocase_collation)
        #self.conn.text_factory = lambda data: str(data, encoding='utf8', errors='surrogateescape')
        self.conn.create_function('CASEFOLD', 1, lambda v: v.casefold(), deterministic=True)
        self.cur = self.conn.cursor()
        if not self.cur:
            logging.error(f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID')
        else:
            #self.cur.execute('PRAGMA ENCODING=UTF16;')
            #self.cur.execute('CREATE TABLE IF NOT EXISTS products(id UNIQUE PRIMARY KEY, name VARCHAR COLLATE UNOCASE, article VARCHAR COLLATE UNOCASE, barcodes VARCHAR, qrcodes VARCHAR COLLATE UNOCASE, cost REAL, price REAL, currency BLOB, unit BLOB, grp BLOB);')
            #self.cur.execute('CREATE INDEX IF NOT EXISTS prods ON products (name COLLATE UNOCASE, article COLLATE UNOCASE, barcodes, qrcodes COLLATE UNOCASE);')
            #self.cur.execute('REINDEX prods;')
            self.cur.execute('CREATE TABLE IF NOT EXISTS products(id UNIQUE PRIMARY KEY, name VARCHAR , article VARCHAR, barcodes VARCHAR, qrcodes VARCHAR, cost REAL, price REAL, currency BLOB, unit BLOB, grp BLOB);')
            self.cur.execute('CREATE TABLE IF NOT EXISTS records(doc_type VARCHAR DEFAULT "sale", registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, product INTEGER, count REAL, cost REAL DEFAULT 0.0, price REAL, sum_final REAL, currency BLOB);')

    def __del__(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    #def nocase_collation(self, a: str, b: str):
        #if a.casefold() == b.casefold():
            #return 0
        #if a.casefold() < b.casefold():
            #return -1
        #return 1

    def product_as_dict(self, v):
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
        return {'rowid':v[0], 'doc_type':v[1], 'registered_at':v[2], 'product':v[3], 'count':v[4], 'cost':v[5], 'price':v[6], 'sum_final':v[7], 'currency':eval(v[8]) if v[8] else {}}

    def update_products(self, *args, **kwargs):
        updated = 0
        if not self.cur:
            return updated, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID'
        data = kwargs.get('data', [])
        logging.debug(['👌RECEIVED PRODUCTS👌', len(data)])
        if data:
            try:
                self.cur.executemany('INSERT INTO products VALUES(:id, :name, :article, :barcodes, :qrcodes, :cost, :price, :currency, :unit, :grp);', data)
            except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                if 'UNIQUE constraint failed' not in f'{e}':
                    logging.debug(['UPDATED PRODUCTS EXECUTEMANY INSERT', e])
                try:
                    self.cur.executemany('UPDATE products SET name=:name, article=:article, barcodes=:barcodes, qrcodes=:qrcodes, cost=:cost, price=:price, currency=:currency, unit=:unit, grp=:grp WHERE id=:id;', data)
                except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                    logging.debug(['UPDATED PRODUCTS EXECUTEMANY UPDATE', e])
                    for v in data:
                        sql_query = f'''UPDATE products SET name='{v["name"]}', article='{v["article"]}', barcodes="{v['barcodes']}", qrcodes="{v['qrcodes']}", cost='{v["cost"]}', price='{v["price"]}', currency="{v['currency']}", unit="{v['unit']}", grp="{v['grp']}" WHERE id={v['id']};'''
                        try:
                            self.cur.execute(sql_query)
                        except Exception as e:
                            logging.debug([e, sql_query])
                        else:
                            updated += 1
                    #logging.debug(['UPDATED PRODUCTS', updated])
                except Exception as e:
                    return updated, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} {e}'
                else:
                    logging.debug('👌EXECUTEMANY UPDATE SUCCESS')
                    updated = self.cur.rowcount
            except Exception as e:
                return updated, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}{e}'
            else:
                logging.debug('👌EXECUTEMANY INSERT SUCCESS')
                updated = self.cur.rowcount
            #self.conn.commit()
        #if updated:
            #self.cur.execute('REINDEX prods;')
        logging.debug(['👌UPDATED PRODUCTS👌', updated])
        return updated, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} SUCCESS'

    def get_product(self, *args, **kwargs):
        if not self.cur:
            return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID'
        if not len(args):
            return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} EMPTY SEARCH STRING'
        result = None
        s = args[0]
        if not isinstance(s, (int, float)) and not s:
            return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} EMPTY SEARCH STRING [{s}]'
        #where_exp = f'''WHERE name LIKE ('%{s}%') OR article='{s}' OR barcodes LIKE ('%{s}%') OR qrcodes LIKE ('%{s}%')'''
        where_exp = f'''WHERE CASEFOLD(name) LIKE ('%{f"{s}".casefold()}%') OR article='{s}' OR barcodes LIKE ('%{s}%') OR qrcodes LIKE ('%{s}%')'''
        if s.isdigit():
            where_exp += f' OR id={s}'
        sql_search = f'SELECT * FROM products {where_exp} LIMIT 1;'
        logging.debug(['✅☑GET_PRODUCT☑✅', sql_search])
        try:
            res = self.cur.execute(sql_search)
        except Exception as e:
            return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}: {sql_search} {e}'
        else:
            v = res.fetchone()
            if v:
                result = self.product_as_dict(v)
        return result, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} SUCCESS'

    def get_products(self, *args, **kwargs):
        if not self.cur:
            return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID'
        limit, offset = kwargs.get('limit', 10), kwargs.get('offset', 0)
        res = self.cur.execute(f'SELECT * FROM products LIMIT {limit} OFFSET {offset};')
        result = None
        if res:
            result = [self.product_as_dict(v) for v in res.fetchall()]
        logging.debug(result)
        return result, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} SUCCESS'

    def get_products_count(self, *args, **kwargs):
        if not self.cur:
            return 0, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID'
        sql_count = 'SELECT COUNT(id) FROM products;'
        logging.debug(['✅☑GET_PRODUCTS_COUNT☑✅', sql_count])
        try:
            res = self.cur.execute(sql_count)
        except Exception as e:
            return 0, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}: {sql_count} {e}'
        else:
            return res.fetchone()[0], f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} SUCCESS'
        return 0, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} UNKNOWN ERROR'

    def insert_records(self, data):
        if not self.cur:
            return False, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID'
        if not data:
            return False, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} EMPTY DATA'
        else:
            try:
                self.cur.executemany('INSERT INTO records VALUES(:doc_type, :registered_at, :product, :count, :cost, :price, :sum_final, :currency)', data)
            except Exception as e:
                return False, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} {e}'
        return True, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} SUCCESS'

    def get_grouped_records(self, *args, **kwargs):
        if not self.cur:
            return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID'
        sqlite3.register_converter('timestamp', lambda v: int(v))
        regs = self.cur.execute('SELECT registered_at FROM records GROUP BY registered_at ORDER BY registered_at;')
        result = []
        regs_list = regs.fetchall()
        sqlite3.register_converter('timestamp', convert_timestamp)
        for reg in regs_list:
            if not reg:
                logging.debug(['GET_GROUPED_RECORDS STRANGE registered_at', reg])
            else:
                sql_query = f'SELECT rowid,* FROM records WHERE registered_at={reg[0]};'
                logging.debug(sql_query)
                res = self.cur.execute(sql_query)
                if res:
                    result.append([self.record_as_dict(v) for v in res.fetchall()])
        if result and result[0]:
            logging.debug(['GET_GROUPED_RECORDS', result])
            return result, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} SUCCESS'
        return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} EMPTY RECORDS'

    def clear_records(self, ids: list):
        if not self.cur:
            return None, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} CURSOR INVALID'
        sql_query = f'DELETE FROM records WHERE rowid IN {tuple(ids)};'
        logging.debug(sql_query)
        self.cur.execute(sql_query)
        return self.cur.rowcount, f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name} FINISHED'
