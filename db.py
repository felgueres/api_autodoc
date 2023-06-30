# contains db creation and utilities for sqlite3 
import sqlite3
from constants import SQLITE_DB

sql_create_users_table = '''
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT NOT NULL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  user_group TEXT NOT NULL DEFAULT 'free'
  );
'''

sql_create_usage_table = '''
CREATE TABLE IF NOT EXISTS usage (
    user_id TEXT NOT NULL PRIMARY KEY,
    n_chatbots INTEGER NOT NULL DEFAULT 0,
    n_sources INTEGER NOT NULL DEFAULT 0,
    n_tokens INTEGER NOT NULL DEFAULT 0,
    n_messages INTEGER NOT NULL DEFAULT 0
    );
'''

sql_create_embeddings_table = '''
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    n_tokens INTEGER NOT NULL,
    embeddings TEXT NOT NULL,
    source_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT NOT NULL DEFAULT '{}')
'''

sql_create_data_table = '''
CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    dtype TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    n_tokens INTEGER NOT NULL DEFAULT 0
    );
    '''

sql_create_blob_table = '''
CREATE TABLE IF NOT EXISTS blobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    data BLOB NOT NULL,
    dtype TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES data_sources(source_id) ON DELETE CASCADE
    );
'''

sql_create_chat_table = '''
CREATE TABLE IF NOT EXISTS chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chatbot_id TEXT NOT NULL,
    is_visible INTEGER NOT NULL DEFAULT 1 
    );
'''

sql_create_bots_table = '''
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    source_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_id TEXT NOT NULL,
    system_message TEXT,
    temperature REAL NOT NULL DEFAULT 0.25,
    metadata TEXT NOT NULL DEFAULT '{}',
    visibility TEXT NOT NULL DEFAULT 'private' 
    );
'''


sql_create_templates_table = '''
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fields TEXT NOT NULL DEFAULT '{}');
'''


sql_create_temp_links_table = '''
CREATE TABLE IF NOT EXISTS temp_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    link_id TEXT NOT NULL,
    url TEXT NOT NULL,
    n_tokens INTEGER NOT NULL DEFAULT 0,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
'''

sql_create_reactions_table = '''
CREATE TABLE IF NOT EXISTS reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    reaction TEXT NOT NULL DEFAULT 'like',
    FOREIGN KEY(bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
'''

def create_table(sql):
    with sqlite3.connect(SQLITE_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()

def write_to_db(sql, entry=None):
    with sqlite3.connect(SQLITE_DB) as conn:
        cursor = conn.cursor()
        if entry:
            cursor.execute(sql, entry)
        else:
            cursor.execute(sql)
        conn.commit()

def write_many_to_db(sql, entries):
    with sqlite3.connect(SQLITE_DB) as conn:
        cursor = conn.cursor()
        cursor.executemany(sql, entries)
        conn.commit()

def read_from_db(sql, entry=None):
    with sqlite3.connect(SQLITE_DB, uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, entry) if entry else cursor.execute(sql)
        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        entries = []
        for row in rows:
            entries.append(dict(zip(col_names, row)))
        return entries

def create_store():
    create_table(sql_create_users_table)
    create_table(sql_create_data_table)
    create_table(sql_create_chat_table)
    create_table(sql_create_bots_table)
    create_table(sql_create_embeddings_table)
    create_table(sql_create_usage_table)
    create_table(sql_create_temp_links_table)
    create_table(sql_create_blob_table)
    create_table(sql_create_reactions_table)
    create_table(sql_create_templates_table)
