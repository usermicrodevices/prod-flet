table_formats = {
'products':'(id UNIQUE PRIMARY KEY, name VARCHAR , article VARCHAR, barcodes VARCHAR, qrcodes VARCHAR, cost REAL, price REAL, currency BLOB, unit BLOB, grp BLOB)',
'records':'(doc_type VARCHAR DEFAULT "sale", registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, product INTEGER, count REAL, cost REAL DEFAULT 0.0, price REAL, sum_final REAL, currency BLOB, customer BLOB)',
'customers':'(id UNIQUE PRIMARY KEY, name VARCHAR, extinfo BLOB)'
}

from log_tools import *
import datetime, sqlite3, sys, threading

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
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(kwargs.get('file_name', 'prod.db'), autocommit=True, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.create_function('CASEFOLD', 1, lambda v: v.casefold(), deterministic=True)
        self.cur = self.conn.cursor()
        if not self.cur:
            self.log(LE, ['CURSOR INVALID'])
        else:
            self.check_tables()
        # CACHE
        self.cachepath = kwargs.get('cache_path', 'file::memory:?cache=shared')
        self.cache = sqlite3.connect(self.cachepath, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cache.create_function('CASEFOLD', 1, lambda v: v.casefold(), deterministic=True)
        self.cur_cache = self.cache.cursor()
        if not self.cur_cache:
            self.log(LE, ['CACHE CURSOR INVALID'])
        else:
            self.update_cache()

    def __del__(self):
        self.lock.acquire(True)
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        self.lock.release()

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

    def drop_table(self, name):
        sql_expr = f'DROP TABLE {name};'
        try:
            self.cur.execute(sql_expr)
        except Exception as e:
            self.log(LE, [sql_expr, e])
        else:
            self.log(LI, ['UNKNOWN-OR-OLD-TABLE', name, 'DELETED'])
            return True
        return False

    def check_table_and_drop(self, name):
        sql_expr = f'SELECT COUNT(*) FROM {name};'
        try:
            res = self.cur.execute(sql_expr)
        except Exception as e:
            self.log(LE, [sql_expr, e])
        else:
            count_records = res.fetchone()[0]
            if count_records:
                self.log(LI, ['IN-TABLE', name, 'COUNT-RECORDS', count_records, 'IMPOSSIBLE-TO-DELETE'])
            else:
                return self.drop_table(name)
        return False

    def check_tables(self):
        exists_tables = []
        sql_expr = 'SELECT name,sql FROM main.sqlite_master WHERE type="table";'
        try:
            res = self.cur.execute(sql_expr)
        except Exception as e:
            self.log(LE, [sql_expr, e])
        else:
            for k, v in res.fetchall():
                if k not in exists_tables:
                    exists_tables.append(k)
                must_be_create = False
                if k not in table_formats:
                    self.log(LW, ['UNKNOWN-OR-OLD-TABLE', k, v])
                    if self.check_table_and_drop(k):
                        exists_tables.remove(k)
                    continue
                table_format = table_formats.get(k, '')
                if not table_format:
                    self.log(LW, ['INVALID-FORMAT-TABLE', k])
                    continue
                if table_format not in v:
                    if k == 'records':
                        if self.check_table_and_drop(k):
                            if k in exists_tables:
                                exists_tables.remove(k)
                        else:
                            new_name = f'{k}_{int(datetime.datetime.now().timestamp())}'
                            sql_expr = f'ALTER TABLE {k} RENAME TO {new_name};'
                            try:
                                res = self.cur.execute(sql_expr)
                            except Exception as e:
                                self.log(LE, [sql_expr, e])
                            else:
                                self.log(LI, ['OLD-TABLE', k, 'RENAMED-TO', new_name])
                                if k in exists_tables:
                                    exists_tables.remove(k)
                                if new_name not in exists_tables:
                                    exists_tables.append(new_name)
                    else:
                        if self.drop_table(k):
                            if k in exists_tables:
                                exists_tables.remove(k)
        for k, v in table_formats.items():
            if k not in exists_tables:
                sql_expr = f'CREATE TABLE IF NOT EXISTS {k}{v};'
                try:
                    self.cur.execute(sql_expr)
                except Exception as e:
                    self.log(LE, [sql_expr, e])
                else:
                    exists_tables.append(k)
                    self.log(LI, ['NEW-TABLE', k, 'CREATED'])
        self.log(LI, ['EXISTS-TABLES', exists_tables])

    def update_cache(self, cache_path: str = '', table_names: list = ['products', 'customers']):
        if not cache_path:
            cache_path = self.cachepath
        self.lock.acquire(True)
        sql_expr = f"ATTACH DATABASE '{cache_path}' AS cache;"
        try:
            self.cur.execute(sql_expr)
        except Exception as e:
            self.log(LE, [sql_expr, e])
        else:
            self.log(LI, ['SUCCESS', sql_expr])
            for tname in table_names:
                sql_expr = f'DROP TABLE IF EXISTS {tname};'
                try:
                    self.cur_cache.execute(sql_expr)
                except Exception as e:
                    self.log(LE, [sql_expr, e])
                else:
                    self.log(LI, ['CACHE-TABLE', tname, 'DROPED'])
                    sql_expr = f'CREATE TABLE {tname}{table_formats[tname]};'
                    try:
                        self.cur_cache.execute(sql_expr)
                    except Exception as e:
                        self.log(LE, [sql_expr, e])
                    else:
                        self.log(LI, ['CACHE-TABLE', tname, 'CREATED'])
                        sql_expr = f'INSERT INTO cache.{tname} SELECT * FROM main.{tname};'
                        try:
                            self.cur.execute(sql_expr)
                        except Exception as e:
                            self.log(LE, [sql_expr, e])
                        else:
                            self.log(LI, ['SUCCESS', sql_expr])
            sql_expr = 'DETACH cache;'
            try:
                self.cur.execute(sql_expr)
            except Exception as e:
                self.log(LE, [sql_expr, e])
            else:
                self.log(LI, ['SUCCESS', sql_expr])
        self.lock.release()

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
        return {'rowid':v[0],
            'doc_type':v[1],
            'registered_at':v[2],
            'product':v[3],
            'count':v[4],
            'cost':v[5],
            'price':v[6],
            'sum_final':v[7],
            'currency':eval(v[8]) if v[8] else {},
            'customer':eval(v[9]) if v[9] else {}
        }

    def customer_as_dict(self, v):
        return {'id':v[0], 'name':v[1], 'extinfo':eval(v[2]) if v[2] else {}}

    def update_products(self, *args, **kwargs):
        updated = 0
        if not self.cur:
            return updated, f'{self.method_name} CURSOR INVALID'
        data = kwargs.get('data', [])
        self.log(LD, ['👌RECEIVED PRODUCTS👌', len(data)])
        if data:
            self.lock.acquire(True)
            try:
                self.cur.executemany('INSERT OR REPLACE INTO products VALUES(:id, :name, :article, :barcodes, :qrcodes, :cost, :price, :currency, :unit, :grp);', data)
            except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                if 'UNIQUE constraint failed' not in f'{e}':
                    self.log(LD, ['UPDATED PRODUCTS EXECUTEMANY INSERT', e])
                try:
                    self.cur.executemany('UPDATE products SET name=:name, article=:article, barcodes=:barcodes, qrcodes=:qrcodes, cost=:cost, price=:price, currency=:currency, unit=:unit, grp=:grp WHERE id=:id;', data)
                except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                    self.log(LD, ['UPDATED PRODUCTS EXECUTEMANY UPDATE', e])
                    for v in data:
                        sql_query = f'''UPDATE products SET name='{v["name"]}', article='{v["article"]}', barcodes="{v['barcodes']}", qrcodes="{v['qrcodes']}", cost='{v["cost"]}', price='{v["price"]}', currency="{v['currency']}", unit="{v['unit']}", grp="{v['grp']}" WHERE id={v['id']};'''
                        try:
                            self.cur.execute(sql_query)
                        except Exception as e:
                            self.log(LE, [sql_query, e])
                        else:
                            updated += 1
                except Exception as e:
                    self.lock.release()
                    return updated, f'{self.method_name} {e}'
                else:
                    self.log(LD, ['👌EXECUTEMANY UPDATE SUCCESS'])
                    updated = self.cur.rowcount
            except Exception as e:
                self.lock.release()
                return updated, f'{self.method_name}{e}'
            else:
                self.log(LD, ['👌EXECUTEMANY INSERT SUCCESS'])
                updated = self.cur.rowcount
            self.lock.release()
        self.log(LD, ['👌UPDATED PRODUCTS👌', updated])
        return updated, f'{self.method_name} SUCCESS'

    def search_products(self, *args, **kwargs):
        result = []
        if not self.cur_cache:
            return result, f'{self.method_name} CURSOR INVALID'
        if not len(args):
            return result, f'{self.method_name} EMPTY SEARCH STRING'
        s = args[0]
        if not isinstance(s, (int, float)) and not s:
            return result, f'{self.method_name} EMPTY SEARCH STRING [{s}]'
        where_exp = f'''WHERE CASEFOLD(name) LIKE ('%{f"{s}".casefold()}%') OR article='{s}' OR barcodes LIKE ('%{s}%') OR qrcodes LIKE ('%{s}%')'''
        if s.isdigit():
            where_exp += f' OR id={s}'
        sql_search = f'SELECT * FROM products {where_exp}{kwargs.get("limit_expression", "")};'
        self.log(LD, ['✅☑SEARCH_PRODUCTS☑✅', sql_search])
        self.lock.acquire(True)
        try:
            res = self.cur_cache.execute(sql_search)
        except Exception as e:
            self.lock.release()
            return result, f'{self.method_name}: {sql_search} {e}'
        else:
            result = [self.product_as_dict(v) for v in res.fetchall()]
        self.lock.release()
        return result, f'{self.method_name} SUCCESS'

    def get_products(self, *args, **kwargs):
        if not self.cur:
            return None, f'{self.method_name} CURSOR INVALID'
        limit, offset = kwargs.get('limit', 10), kwargs.get('offset', 0)
        self.lock.acquire(True)
        res = self.cur.execute(f'SELECT * FROM products LIMIT {limit} OFFSET {offset};')
        result = None
        if res:
            result = [self.product_as_dict(v) for v in res.fetchall()]
        self.lock.release()
        self.log(LD, [result])
        return result, f'{self.method_name} SUCCESS'

    def get_products_count(self, *args, **kwargs):
        if not self.cur:
            return 0, f'{self.method_name} CURSOR INVALID'
        sql_count = 'SELECT COUNT(id) FROM products;'
        self.log(LD, ['✅☑GET_PRODUCTS_COUNT☑✅', sql_count])
        self.lock.acquire(True)
        try:
            res = self.cur.execute(sql_count)
        except Exception as e:
            self.lock.release()
            return 0, f'{self.method_name}: {sql_count} {e}'
        else:
            result = res.fetchone()[0]
            self.lock.release()
            return result, f'{self.method_name} SUCCESS'
        self.lock.release()
        return 0, f'{self.method_name} UNKNOWN ERROR'

    def clear_products(self):
        if not self.cur:
            return 0, f'{self.method_name} CURSOR INVALID'
        sql_query = f'DELETE FROM products;'
        self.log(LD, [sql_query])
        self.lock.acquire(True)
        try:
            self.cur.execute(sql_query)
        except Exception as e:
            self.lock.release()
            self.log(LE, [sql_query, e])
            return 0, f'{self.method_name} ERROR: {e}'
        self.lock.release()
        return self.cur.rowcount, f'{self.method_name} FINISHED'

    def insert_records(self, data):
        if not self.cur:
            return False, f'{self.method_name} CURSOR INVALID'
        if not data:
            return False, f'{self.method_name} EMPTY DATA'
        else:
            #self.log(LI, [data])
            self.lock.acquire(True)
            try:
                self.cur.executemany('INSERT INTO records VALUES(:doc_type, :registered_at, :product, :count, :cost, :price, :sum_final, :currency, :customer)', data)
            except Exception as e:
                self.lock.release()
                return False, f'{self.method_name} {e}'
            self.lock.release()
        return True, f'{self.method_name} SUCCESS'

    def get_grouped_records(self, *args, **kwargs):
        if not self.cur:
            return None, f'{self.method_name} CURSOR INVALID'
        sqlite3.register_converter('timestamp', lambda v: int(v))
        self.lock.acquire(True)
        regs = self.cur.execute('SELECT registered_at FROM records GROUP BY registered_at ORDER BY registered_at;')
        result = []
        regs_list = regs.fetchall()
        sqlite3.register_converter('timestamp', convert_timestamp)
        for reg in regs_list:
            if not reg:
                self.log(LD, ['GET_GROUPED_RECORDS STRANGE registered_at', reg])
            else:
                sql_query = f'SELECT rowid,* FROM records WHERE registered_at={reg[0]};'
                self.log(LD, [sql_query])
                res = self.cur.execute(sql_query)
                if res:
                    result.append([self.record_as_dict(v) for v in res.fetchall()])
        self.lock.release()
        if result and result[0]:
            self.log(LD, ['GET_GROUPED_RECORDS', result])
            return result, f'{self.method_name} SUCCESS'
        return None, f'{self.method_name} EMPTY RECORDS'

    def clear_records(self, ids: list):
        if not self.cur:
            return 0, f'{self.method_name} CURSOR INVALID'
        if not ids:
            return 0, f'{self.method_name} INDEXES EMPTY'
        sql_list_ids = f'({ids[0]})' if len(ids) == 1 else f'{tuple(ids)}'
        sql_query = f'DELETE FROM records WHERE rowid IN {sql_list_ids};'
        self.log(LD, [sql_query])
        count_records = 0
        self.lock.acquire(True)
        try:
            self.cur.execute(sql_query)
        except Exception as e:
            self.lock.release()
            self.log(LE, [sql_query, e])
            return count_records, f'{self.method_name} ERROR: {e}'
        else:
            count_records = self.cur.rowcount
        self.lock.release()
        return count_records, f'{self.method_name} FINISHED'

    def update_customers(self, *args, **kwargs):
        updated = 0
        if not self.cur:
            return updated, f'{self.method_name} CURSOR INVALID'
        data = kwargs.get('data', [])
        self.log(LD, ['🆗✌RECEIVED CUSTOMERS✌🆗', len(data)])
        if data:
            self.lock.acquire(True)
            try:
                self.cur.executemany('INSERT OR REPLACE INTO customers VALUES(:id, :name, :extinfo);', data)
            except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                if 'UNIQUE constraint failed' not in f'{e}':
                    self.log(LD, ['UPDATED CUSTOMERS EXECUTEMANY INSERT', e])
                try:
                    self.cur.executemany('UPDATE customers SET name=:name, extinfo=:extinfo WHERE id=:id;', data)
                except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                    self.log(LD, ['UPDATED CUSTOMERS EXECUTEMANY UPDATE', e])
                    for v in data:
                        sql_query = f'''UPDATE customers SET name='{v["name"]}', extinfo="{v['extinfo']}" WHERE id={v['id']};'''
                        try:
                            self.cur.execute(sql_query)
                        except Exception as e:
                            self.log(LE, [sql_query, e])
                        else:
                            updated += 1
                except Exception as e:
                    self.lock.release()
                    return updated, f'{self.method_name} {e}'
                else:
                    self.log(LD, ['🆗✌EXECUTEMANY UPDATE SUCCESS'])
                    updated = self.cur.rowcount
            except Exception as e:
                self.lock.release()
                return updated, f'{self.method_name}{e}'
            else:
                self.log(LD, ['🆗✌EXECUTEMANY INSERT SUCCESS'])
                updated = self.cur.rowcount
            self.lock.release()
        self.log(LD, ['🆗✌UPDATED CUSTOMERS✌🆗', updated])
        return updated, f'{self.method_name} SUCCESS'

    def search_customers(self, *args, **kwargs):
        result = []
        if not self.cur_cache:
            return result, f'{self.method_name} CURSOR INVALID'
        if not len(args):
            return result, f'{self.method_name} EMPTY SEARCH STRING'
        s = args[0]
        if not isinstance(s, (int, float)) and not s:
            return result, f'{self.method_name} EMPTY SEARCH STRING [{s}]'
        where_exp = f'''WHERE CASEFOLD(name) LIKE ('%{f"{s}".casefold()}%')'''
        if s.isdigit() and kwargs.get('search_id', False):
            where_exp += f' OR id={s}'
        sql_search = f'SELECT * FROM customers {where_exp}{kwargs.get("limit_expression", "")};'
        self.log(LD, ['🆗✌SEARCH_CUSTOMERS✌🆗', sql_search])
        self.lock.acquire(True)
        try:
            res = self.cur_cache.execute(sql_search)
        except Exception as e:
            self.lock.release()
            return result, f'{self.method_name}: {sql_search} {e}'
        else:
            result = [self.customer_as_dict(v) for v in res.fetchall()]
        self.lock.release()
        return result, f'{self.method_name} SUCCESS'

    def get_customers(self, *args, **kwargs):
        if not self.cur:
            return None, f'{self.method_name} CURSOR INVALID'
        limit, offset = kwargs.get('limit', 10), kwargs.get('offset', 0)
        self.lock.acquire(True)
        res = self.cur.execute(f'SELECT * FROM customers LIMIT {limit} OFFSET {offset};')
        result = None
        if res:
            result = [self.customer_as_dict(v) for v in res.fetchall()]
        self.lock.release()
        self.log(LD, [result])
        return result, f'{self.method_name} SUCCESS'

    def get_customers_count(self, *args, **kwargs):
        if not self.cur:
            return 0, f'{self.method_name} CURSOR INVALID'
        sql_count = 'SELECT COUNT(id) FROM customers;'
        self.log(LD, ['🆗✌GET_CUSTOMERS_COUNT✌🆗', sql_count])
        self.lock.acquire(True)
        try:
            res = self.cur.execute(sql_count)
        except Exception as e:
            self.lock.release()
            return 0, f'{self.method_name}: {sql_count} {e}'
        else:
            result = res.fetchone()[0]
            self.lock.release()
            return result, f'{self.method_name} SUCCESS'
        self.lock.release()
        return 0, f'{self.method_name} UNKNOWN ERROR'

    def clear_customers(self):
        if not self.cur:
            return 0, f'{self.method_name} CURSOR INVALID'
        sql_query = f'DELETE FROM customers;'
        self.log(LD, [sql_query])
        self.lock.acquire(True)
        try:
            self.cur.execute(sql_query)
        except Exception as e:
            self.lock.release()
            self.log(LE, [sql_query, e])
            return 0, f'{self.method_name} ERROR: {e}'
        self.lock.release()
        return self.cur.rowcount, f'{self.method_name} FINISHED'
