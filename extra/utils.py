import os
import secrets
import jinja2

def fill_html(path, **kwargs):
    with open(path, 'r') as f: html = f.read()
    template = jinja2.Template(html)
    return template.render(**kwargs)

def generate_uuid(length=16):
    return secrets.token_hex(length)

def join_path(a,b):
    return os.path.join(a,b)

def get_base_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_query_folder():
    return join_path(get_base_path(), 'query')

def read_query(qname:str) -> str:
    qpath = join_path(get_query_folder(), qname+'.sql')
    with open(qpath, 'r') as f: q = f.read()
    return q