from log_tools import *

def db_update_products(page, data_prods):
    count_updated = 0
    if data_prods:
        count_updated, msg = page.db_conn.update_products(data=data_prods)
        logging.debug(['UPDATED_PRODUCTS', count_updated, msg])
    return count_updated

def sync_products(page):
    if page.sync_products_running:
        logging.debug('sync_products is running now')
        return
    page.sync_products_running = True
    if page.http_conn.auth_success:
        headers, prods = page.http_conn.get_products_cash()
        updated_products = db_update_products(page, prods)
        full_products, msg = page.db_conn.get_products_count()
        page.update_status_ctrl({0:f'{full_products}🧷{updated_products}'})
        page_max = int(headers.get('page_max', 0))
        logging.debug(['PAGE_MAX', page_max])
        if page_max > 1:
            for p in range(2, page_max):
                headers, prods = page.http_conn.get_products_cash(p)
                updated_products += db_update_products(page, prods)
                full_products, msg = page.db_conn.get_products_count()
                page.update_status_ctrl({0:f'{full_products}🧷{updated_products}'})
        if updated_products:
            page.db_conn.update_cache(table_names=['products'])
    else:
        logging.debug(['SYNC_PRODUCTS', 'AUTH NOT EXISTS'])
        status_code = page.http_conn.auth()
    page.sync_products_running = False

def db_update_customers(page, data_customers):
    count_updated = 0
    if data_customers:
        count_updated, msg = page.db_conn.update_customers(data=data_customers)
        logging.debug(['UPDATED_CUSTOMERS', count_updated, msg])
    return count_updated

def sync_customers(page):
    if page.sync_customers_running:
        logging.debug('sync_customers is running now')
        return
    page.sync_customers_running = True
    if page.http_conn.auth_success:
        headers, customers = page.http_conn.get_customers()
        updated_customers = db_update_customers(page, customers)
        full_customers, msg = page.db_conn.get_customers_count()
        page.update_status_ctrl({5:f'{full_customers}🧷{updated_customers}'})
        page_max = int(headers.get('page_max', 0))
        logging.debug(['PAGE_MAX', page_max])
        if page_max > 1:
            for p in range(2, page_max):
                headers, customers = page.http_conn.get_customers(p)
                updated_customers += db_update_customers(page, customers)
                full_customers, msg = page.db_conn.get_customers_count()
                page.update_status_ctrl({0:f'{full_customers}🧷{updated_customers}'})
        if updated_customers:
            page.db_conn.update_cache(table_names=['customers'])
    else:
        logging.debug(['SYNC_PRODUCTS', 'AUTH NOT EXISTS'])
        status_code = page.http_conn.auth()
    page.sync_products_running = False

def sync_sales(page):
    recs, msg = page.db_conn.get_grouped_records()
    if not recs:
        logging.debug(msg)
    else:
        for doc_recs in recs:
            frec = doc_recs[0]
            data = {'sum_final':float(frec['sum_final']), 'registered_at':frec['registered_at'].strftime('%Y-%m-%dT%H:%M:%S %z'), 'type':frec['doc_type'], 'customer':frec['customer']}
            records, rowids = [], []
            for rec in doc_recs:
                record = {'product':rec['product'], 'count':rec['count'], 'price':rec['price'], 'currency_id':rec['currency']['id']}
                records.append(record)
                rowids.append(rec['rowid'])
            data['records'] = records
            sended = False
            if page.http_conn.auth_success:
                sended = page.http_conn.post_doc_cash(data)
                logging.debug(['SALE FINISH SEND TO SERVER', sended])
            if not sended:
                logging.debug('CONNECTION ERROR')
                status_code = page.http_conn.auth()
                break
            elif rowids:
                cleared_count, msg = page.db_conn.clear_records(rowids)
                logging.debug(['CLEARED LOCAL RECORDS', cleared_count, msg])
