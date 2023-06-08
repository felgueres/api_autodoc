import threading
import time
from constants import SQLITE_DB, DATA_SOURCES_TABLE
from  db_utils import write_to_db, read_from_db
from embeddings import pdf_to_embeddings, txt_to_embeddings, url_to_embeddings

import logging as pylogging
logger = pylogging.getLogger(__name__)

class FileQueue:
    def __init__(self, db_path=SQLITE_DB, table_name=DATA_SOURCES_TABLE, max_size=30):
        '''
        db_path: path to the sqlite3 database
        table_name: name of the table to use
        max_size: maximum number of items to store in the queue
        '''
        self.db_path = db_path
        self.table_name = table_name
        self.max_size = max_size
        self.processing_cnt = 0
        self.lock = threading.Lock()

    def start_processing(self):
        '''Start processing files in queue
        '''
        t = threading.Thread(target=self.process_files)
        t.start()
    
    def add(self, user, fname, dtype, source_id=None):
        '''Add file to db and return source_id
        '''
        from utils import generate_uuid
        source_id = generate_uuid(length=8) if not source_id else source_id
        add_file_q = f'INSERT INTO {DATA_SOURCES_TABLE} (source_id,user_id,name,dtype) VALUES (?,?,?,?)'
        file_entry = [source_id,user,fname,dtype]
        with self.lock:
            write_to_db(add_file_q, file_entry)
        return source_id
    
    def get_file(self):
        '''Get pending from db
        Returns filename: str
        '''
        read_q = f'SELECT source_id, user_id, name, status, dtype FROM {DATA_SOURCES_TABLE} WHERE status = "pending" ORDER BY created_at ASC LIMIT 1'
        with self.lock:
            result = read_from_db(read_q)
            result = result[0] if result else None 
            if result:
                update_q = f'UPDATE {DATA_SOURCES_TABLE} SET status = "processing" WHERE source_id = ?'
                write_to_db(update_q, [result['source_id']])
                self.processing_cnt += 1
                return result
            else:
                return None
    
    def process_files(self):
        '''Process files in queue
        '''
        while True:
            if self.processing_cnt < self.max_size:
                result = self.get_file()
                if result:
                    fname = result['name']
                    user_id = result['user_id']
                    dtype = result['dtype']
                    source_id = result['source_id']
                    if fname.lower().endswith('.pdf'):
                        processing_output = pdf_to_embeddings(fname=fname, user_id=user_id, source_id=source_id)
                    elif fname.lower().endswith('.txt'):
                        processing_output = txt_to_embeddings(fname=fname, user=user_id, source_id=source_id)
                    elif dtype in ['url', 'video']:
                        processing_output = url_to_embeddings(user_id=user_id, source_id=source_id)
                    status = processing_output['status']
                    n_tokens = processing_output['n_tokens']
                    self.mark_as_processed(source_id, user_id, status, n_tokens)
                else:
                    pass
                time.sleep(5)
            else:
                print('Queue is full, sleeping for 10 seconds ...')
                time.sleep(10)
    
    def mark_as_processed(self, source_id, user_id, status, n_tokens):
        '''Mark file as processed
        '''
        print('markigin with', source_id, user_id, status, n_tokens)
        update_q = f'UPDATE {self.table_name} SET status = ?, n_tokens = ? WHERE source_id = ? AND user_id = ?' 
        sql_upsert_sources = f'INSERT INTO usage (user_id, n_chatbots, n_sources, n_tokens, n_messages) VALUES (?, 0, 1, ?, 0) ON CONFLICT(user_id) DO UPDATE SET n_sources = n_sources + 1, n_tokens = n_tokens + ?' 

        with self.lock:
            try:
                write_to_db(update_q, [status, int(n_tokens), source_id, user_id])
                write_to_db(sql_upsert_sources, [user_id, int(n_tokens), int(n_tokens)])
            except Exception as e:
                logger.error(f'Error updating {source_id} for {user_id}: {e}')
            self.processing_cnt -= 1
