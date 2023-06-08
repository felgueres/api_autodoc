# Inputs: PDF file
# Outputs: JSON with key value pairs

####
# Approach A. Rolling window with starting map of key value pairs, where key is the feature is known and value is in the RFQ 
# 1. rolling window of 1000 tokens of content
# 2. if value is not present, then fill JSON with blank
# 3. if value is present, then fill JSON with value 
# 4. Repeat until end of document
# 5. Consolidate JSONs into one, where you provide a list of choices for each key value pair
# 6. Show in the UI 
# 7. User selects the correct value
# 8. User can also edit the value 
# 9. User can export the JSON in CSV format

#### 
# Approach B. Single call to extract all key value pairs using a more powerful model  

# This file implements A
from embeddings import compute_distances, read_embeddings_from_db, get_q_embeddings, fetch_passages
from utils import get_few_shot_loop_json, validate_format, flatten_json
from flask import jsonify
from upstream_object import DataLoader
import json
from serve import InferenceError
from chatapi import chat_completion
from constants import MODEL_MAP

class MissingEmbeddingsError(Exception):
    pass

def extract(data):

    sources_ids = [s['source_id'] for s in data['sources']] if data['sources'] else []
    data['messages'] = []

    try: 
        d_embeddings_df = read_embeddings_from_db(sources_ids)        
        all_sources = fetch_passages(d_embeddings_df, max_passages=1000, sort_by='id', ascending=True)

    except Exception as e:
        print('Error fetching passages', e)
        return jsonify(''), 500

    try:
        # split sources in chunks of two items
        sources = [all_sources[i:i + 2] for i in range(0, len(all_sources), 2)]
        
        data['context'] = '###'.join([s['text'] for s in sources])

        data['context'] = data['context'] + '\n' + \
            '\n Example response \n' + get_few_shot_loop_json() + \
            '\n Make sure the response can be parsed by Python json.loads and only fill in the same key value pairs, if not present, show the key and leave the value empty.'

        chat_inputs = DataLoader.construct_chat(data, api_key='')
        chat_inputs.add_user_message(data["query"])
        messages = chat_inputs.get_messages('facts')
        response, success = chat_completion( model=MODEL_MAP[chat_inputs.model_id], messages=messages, temp=1)
        if not success: raise InferenceError()

        message = response.get('choices', [{}])[0].message
        content = message['content'].strip()

        data = json.loads(content)

        print('\n\n\nRESPONSE:', json.dumps(data, indent=4), '\n\n\n')

        if validate_format(content):
            d = json.loads(content)
            out = {'summary': '', 'facts': flatten_json(d['facts']), 'reference': sources[0]}
            return jsonify(out), 200

        else:
            return jsonify({'summary': 'Couldn\'t find relevant information. Try again.', 'facts': {}, 'reference': {'id': '', 'title': '', 'text': '', 'score': '', 'n_tokens': ''}}), 200

    except Exception as e:
        return jsonify({'summary': 'Couldn\'t find relevant information. Please try again.', 'facts': {}, 'reference': {'id': '', 'title': '', 'text': '', 'score': '', 'n_tokens': ''}}), 200
