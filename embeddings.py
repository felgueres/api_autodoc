import os
import pandas as pd
from logger_config import setup_logger
from constants import DTYPE_PDF, DTYPE_CSV
from upstream_object import DataLoader
from db_utils import read_from_db
from typing import List

logger = setup_logger(__name__)
import json
from chatapi import chat_completion, MODEL_MAP

def remove_newlines(serie):
    serie = serie.str.replace('\n', ' ')
    serie = serie.str.replace('\\n', ' ')
    serie = serie.str.replace('  ', ' ')
    serie = serie.str.replace('  ', ' ')
    return serie

def file_exists(file_path):
    return os.path.isfile(file_path)

def write_out(df, target_path):
    if not os.path.exists(os.path.dirname(target_path)):
        os.makedirs(os.path.dirname(target_path))
    logger.info('writing df: {}'.format(df.head()))
    df.to_csv(target_path, index=False, escapechar='\\')
    logger.info('file write with success: {}'.format(file_exists(target_path)))
    return None

def pdf_to_df(fpath, fname, source_id):
    from PyPDF2 import PdfReader
    with open(fpath, "rb") as f:
        reader = PdfReader(f)
        texts = []
        for i, page in enumerate(reader.pages):
            texts.append((i+1, page.extract_text()))
        df = pd.DataFrame(texts, columns=['page_number', 'text'])
        df['text'] = df.fname + '. ' + remove_newlines(df.text)
        df['source_id'] = source_id
        df.columns = ['page_number', 'text', 'source_id']
    logger.info('success with df shape {}'.format(df.shape))
    return df

# Function to split the text into chunks of a maximum number of tokens
def split_into_many(title, text, tokenizer, max_tokens=500):
    sentences = text.split('. ')
    n_tokens = [len(tokenizer.encode(" " + sentence))
                for sentence in sentences]

    chunks = []
    tokens_so_far = 0
    chunk = []

    for sentence, token in zip(sentences, n_tokens):
        if tokens_so_far + token > max_tokens:
            chunks.append((title, ". ".join(chunk) + "."))
            chunk = []
            tokens_so_far = 0
        if token > max_tokens:
            continue
        chunk.append(sentence)
        tokens_so_far += token + 1

    return chunks

def shorten_text(df, tokenizer, max_tokens=500):
    shortened = []
    for _, row in df.iterrows():
        if row['text'] is None:
            continue
        if row['n_tokens'] > max_tokens:
            shortened += split_into_many(row['title'], row['text'], tokenizer)
        else:
            shortened.append((row['title'],row['text']))
    return shortened

def prepare_df(processed_path, max_tokens=500):
    import tiktoken
    tokenizer = tiktoken.get_encoding("cl100k_base")
    df = pd.read_csv(processed_path, index_col=None)
    df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))
    shortened_df = pd.DataFrame(shorten_text(df, tokenizer, max_tokens), columns=['title', 'text'])
    shortened_df['n_tokens'] = shortened_df.text.apply(lambda x: len(tokenizer.encode(x)))
    return shortened_df

def get_embeddings(df):
    df['embeddings'] = df.text.apply(lambda x: get_q_embeddings(x))
    return df

def pdf_to_embeddings(fname, user_id, source_id):
    from db_utils import write_many_to_db, write_to_db
    fname = os.path.splitext(os.path.basename(fname))[0]  # get filename without extension
    raw_path = f'users/{user_id}/files/{fname}.{DTYPE_PDF}'
    processed_path = f'users/{user_id}/files/processed/{source_id}_{fname}.{DTYPE_CSV}'
    n_tokens = 0

    try:
        with open(raw_path, 'rb') as f:
            data = f.read()
            add_blob_q = '''INSERT INTO blobs (source_id,data,dtype) VALUES (?,?,?)'''
        blob_entry = (source_id, data, DTYPE_PDF)
        write_to_db(add_blob_q, blob_entry)

    except Exception as e:
        logger.info(f'error writing blob: {e}')
        return {'status': 'error', 'reason': e, 'n_tokens': n_tokens }

    try:
        df = pdf_to_df(raw_path, fname, source_id)
        write_out(df, processed_path)

    except Exception as e:
        logger.info(f'error: {e}')
        return {'status': 'error', 'reason': e, 'n_tokens': n_tokens }
    
    try:
        df = prepare_df(processed_path)
        df = get_embeddings(df)
        df['embeddings'] = df.embeddings.apply(lambda x: str(x)) 
        df['source_id'] = source_id
        n_tokens = df.n_tokens.sum()
        df['facts'] = '' 
        entries = [(user_id, title, text, n_tokens, embeddings, source_id, facts) for title, text, n_tokens, embeddings, source_id, facts in df[['title', 'text', 'n_tokens', 'embeddings', 'source_id', 'facts']].values]
        sql_insert_embeddings = '''INSERT INTO embeddings (user_id, title, text, n_tokens, embeddings, source_id, facts) VALUES (?, ?, ?, ?, ?, ?, ?) '''
        logger.info('Writing df out with shape {}'.format(df.shape))
        write_many_to_db(sql_insert_embeddings, entries)
        return {'status': 'success', 'reason': 'Embeddings generated', 'n_tokens': n_tokens}
    except Exception as e:
        logger.info(f'-----\n\n\nERROR PROCESSING EMBEDDINGS: {e} \n\n\n------')
        return {'status': 'error', 'reason': 'Could not generate embeddings', 'n_tokens': n_tokens }


def db_to_df(source_id, user_id):
    url_data_sql = """SELECT * FROM temp_links WHERE source_id = ? AND user_id = ?"""
    data = read_from_db(url_data_sql, [source_id, user_id])
    df = pd.DataFrame(data)
    df.columns = ['id', 'user_id', 'source_id', 'link_id', 'url', 'n_tokens', 'text', 'created_at']
    df['title'] = df.url
    df['text'] = df.url + '. ' + remove_newlines(df.text)
    df = df[['title', 'text', 'source_id']]
    print(df.head())
    return df

def get_facts_from_passage(passage):
    data = {}
    data['messages'] = []
    data['model_id'] = 'gpt3'
    data['context'] = passage + '\n' + 'You should only respond in unnested JSON format as described below. \n Response format: {"facts": {"fact1": "value1", "fact2": "value2"}, "summary": "short summary"} \n Ensure the response can be parsed by Python json.loads' 
    try:
        chat_inputs = DataLoader.construct_chat(data, api_key=os.environ['OPENAI_KEY'])
        messages = chat_inputs.get_messages('facts')
        response = chat_completion(model=MODEL_MAP[chat_inputs.model_id], messages=messages, temp=0.9)
        message = response.get('choices', [{}])[0].message
        content = message['content'].strip()
        facts = json.loads(content)
        return facts 
    except:
        facts = {}
    return facts

def get_passages_from_embeddings(e_df, max_len=1800, n_passages=2):
    cur_len = 0
    sources = [] 
    break_outer = False
    # get the first n_passages for each source inplace
    for source_id in e_df.source_id.unique():
        # get first passage
        _df = e_df[e_df.source_id == source_id].copy().iloc[:1]
        # then sample n passages 
        _df = _df.append(e_df[e_df.source_id == source_id].copy().sample(n_passages))
        for _, row in _df.iterrows():
            cur_len += row['n_tokens'] + 4
            if cur_len > max_len:
                break_outer = True 
                break
            sources.append({'id': row['source_id'],'title': row['title'], 'text': row['text']})
        if break_outer:
            break
    return sources

def read_embeddings_from_db(sources_ids: List[str]):
    import pandas as pd
    import numpy as np
    from db_utils import read_from_db
    embeddings_sql = 'SELECT * FROM embeddings WHERE LENGTH(text) > (LENGTH(title) + 1) AND source_id IN (%s)' % ','.join('?' * len(sources_ids))
    data = read_from_db(embeddings_sql, [*sources_ids]) 
    df = pd.DataFrame(data)
    # check if embeddings are already computed
    if df.embeddings.iloc[0] == '':
        return None
    df['embeddings'] = df.embeddings.apply(eval).apply(np.array)
    print('loading embedings with shape', df.shape)
    return df

def compute_distances(data_df, question_df):
    data_df['distance'] = data_df.embeddings.apply(lambda d_e: cos_sim(question_df, d_e))
    return data_df

def get_q_embeddings(q, engine='text-embedding-ada-002', max_retries=5):
    import openai
    import time
    openai.api_key = os.environ['OPENAI_KEY']
    retry_delay = 1
    backoff = 2
    for i in range(max_retries):
        try:
            q_embeddings = openai.Embedding.create(input=q, engine=engine)['data'][0]['embedding']
            return q_embeddings
        except Exception as e:
            print(f"Error: {e}")
            if i == max_retries - 1:
                return None
            time.sleep(retry_delay)
            retry_delay *= backoff
    return None

def create_context(d_embeddings_df, max_len=2300, max_passages=8):
    cur_len = 0
    refs = [] 
    for i, row in d_embeddings_df.sort_values('distance', ascending=False).reset_index(drop=True).iterrows():
        cur_len += row['n_tokens'] + 4
        if cur_len > max_len or i >= max_passages: # experiment: row['distance'] < 0.5 or (row['distance'] < 0.8 and cur_len > 500):
            break
        print(row['text'], row['distance'])
        refs.append({'id': row['source_id'], 'title': row['title'], 'text': row['text'].replace(row['title'],'').strip()})
    return refs 

def fetch_passages(d_embeddings_df, max_passages=5, sort_by='distance', ascending=False):
    cur_len = 0
    sources = [] 
    for i, row in d_embeddings_df.sort_values(sort_by, ascending=ascending).reset_index(drop=True).iterrows():
        cur_len += row['n_tokens'] + 4
        if i >= max_passages:
            break
        sources.append({'id': row['source_id'],'title': row['title'], 'text': row['text'], 'score': 0, 'n_tokens': row['n_tokens']})
    return sources 

def cos_sim(a,b):
    from numpy import dot 
    from numpy.linalg import norm
    return dot(a, b)/(norm(a)*norm(b))