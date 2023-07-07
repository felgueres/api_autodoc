from . import core_bp
import yaml
from embeddings import read_embeddings_from_db, get_q_embeddings, fetch_passages, compute_distances
from autodoc.utils import get_template
from extra.auth import jwt_auth
from gpt import gpt
from embeddings import read_embeddings_from_db
from flask import jsonify, request
from extra.logger_config import setup_logger

logger = setup_logger(__name__)

@core_bp.route('/v1/search', methods=['POST'])
@jwt_auth
def extract(user_id):
    data = request.json
    template = get_template(data['template_id'])
    sid = data['source_id']
    template_idx = data['field_idx']
    d_embeddings_df = read_embeddings_from_db([sid])
    configs = yaml.safe_load(open('./prompt/prompts.yaml','r'))
    prompt = configs['extract_w_completion']['prompt']
    k, message, page_number = extract_field(template[template_idx], d_embeddings_df, prompt)
    d_out = {'field': k, 'value': message, 'page_number': page_number}
    return jsonify({'object': 'extracted_field', 'data': d_out}), 200

def extract_field(field, d_embeddings_df, prompt):
    k = field['name']
    type = 'string' if field['type'].lower() == 'text' else 'number'
    description = field['description']
    q_embeddings = get_q_embeddings(q=f'What is the {k}?')
    d_embeddings_df = compute_distances(d_embeddings_df, q_embeddings)
    sources = fetch_passages(d_embeddings_df, max_passages=3, sort_by='distance', ascending=False)
    extracts = ['<SOE> Page [' + str(s['page_number']) + '] ' + s['text'] for s in sources]
    extracts = '<EOE>'.join(extracts)
    prompt = prompt.format(extracts=extracts, k=k, type=type, description=description)

    try:
        res = gpt(prompt=prompt)
        message = res['choices'][0]['message']['content'].strip()
        return k, message, sources[0]['page_number'] 

    except Exception as e:
        return k, '', -1
