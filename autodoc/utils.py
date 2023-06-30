from db import read_from_db
from extra.utils import read_query
import json

class RetriableError(Exception):
    pass

def get_template(template_id):
    templateq = read_query('template')
    template = read_from_db(templateq, [template_id])[0]
    fields = json.loads(template['fields'])
    return fields
