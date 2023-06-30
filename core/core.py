from . import core_bp
from embeddings import read_embeddings_from_db, get_q_embeddings, fetch_passages, compute_distances
from core.utils import get_template, RetriableError
from extra.auth import jwt_auth
from gpt import gpt
import concurrent
import json
from embeddings import read_embeddings_from_db
from concurrent.futures import ThreadPoolExecutor
from flask import jsonify, request
import yaml
from extra.logger_config import setup_logger

logger = setup_logger(__name__)

@core_bp.route('/v1/search', methods=['POST'])
@jwt_auth
def extract(user_id):
    data = request.json
    fields = get_template(data['template_id'])
    d_embeddings_df = read_embeddings_from_db([data['sources'][0]['source_id']])
    configs = yaml.safe_load(open('./prompt/prompts.yaml','r'))
    prompt = configs['general_form']['prompt']
    num_threads = 3
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(extract_field, field, d_embeddings_df, prompt) for field in fields]
        d_out = {}
        for future in concurrent.futures.as_completed(futures):
            k,v,pn = future.result()
            logger.info(f'Extracted (k,v,pn): {k} , {v}, {pn}')
            d_out[k] = {'value': v, 'page_number': pn} 
    return jsonify({'facts': d_out}), 200

def extract_field(field, d_embeddings_df, prompt):
    k = field['name']
    type = 'string' if field['type'].lower() == 'text' else 'number'
    description = field['description']
    q_embeddings = get_q_embeddings(q=f'What is the {k}?')
    d_embeddings_df = compute_distances(d_embeddings_df, q_embeddings)
    sources = fetch_passages(d_embeddings_df, max_passages=3, sort_by='distance', ascending=False)
    extracts = ['Page ' + str(s['page_number']) + '. ' + s['text'] for s in sources]
    extracts = '---\n'.join(extracts)

    prompt = prompt.format(extracts=extracts, k=k, type=type, description=description)

    functions = [
        {
            'name': 'extract',
            'description': 'Extract fields from a form given extracts from a filled out form', 
            'parameters': {
                'type': 'object',
                'properties': {
                    k: {
                        'type': type,
                        'description': description
                    },
                    'page_number': {
                        'type': 'number',
                        'description': 'Page number where the extract was found. If the extract is not found, the page number is -1.'
                    }
            },
            'required': [k, 'page_number']}
        }
    ]

    retry_count = 0

    while retry_count < 3:
        try:
            res = gpt(prompt=prompt,functions=functions)
            res = json.loads(res['choices'][0]['message']['function_call']['arguments'])
            if res[k] == '' or res[k] == -1:
                raise RetriableError
            return k, res[k], res['page_number'] 

        except RetriableError:
            retry_count += 1
            if retry_count >= 3:
                return k, '', -1

        except Exception as e:
            return k, '', -1
