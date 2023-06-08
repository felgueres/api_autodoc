from logger_config import setup_logger
from flask import Flask, request, jsonify, render_template, redirect, send_file, Response
from auth import jwt_auth
from chatapi import chat_completion
from dotenv import load_dotenv
from db_utils import create_store, write_to_db, read_from_db, write_many_to_db
from constants import MAX_FILE_SIZE, EMPTY_STRING, USERS_WITH_GPT4, DTYPE_URL, DTYPE_VIDEO, MIMETYPES, PLANS
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Bcc
from utils import fill_html, generate_uuid, flatten_json, validate_format, get_few_shot_loop_json
from upstream_object import DataLoader
import os
from send_email import send_upload_email
from flask_cors import CORS
from werkzeug.utils import secure_filename
from filequeue import FileQueue
from embeddings import read_embeddings_from_db, get_q_embeddings, create_context, fetch_passages
from chatapi import MODEL_MAP
import json
from web import preflight_url_validation_headless
from video import process_youtube_video

logger = setup_logger(__name__)
load_dotenv()
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE  # 16MB
CORS(app)

app.secret_key = os.getenv("SECRET_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
SG_API_KEY = os.getenv("SG_API_KEY")

TEST_STREAM = True 

create_store()
file_queue = FileQueue()

PAYED_CREDITS = 100
FREE_CREDITS = 10

@app.errorhandler(408)
@app.errorhandler(404)
@app.errorhandler(400)
def page_not_found(e):
    return render_template('404.html')

@app.before_first_request
def before_first_request():
    file_queue.start_processing()

@app.route('/')
def index():
    return redirect("https://upstreamapi.com", code=302)

@app.route('/v1/file/<source_id>', methods=['GET'])
@jwt_auth
def get_file(user_id, source_id):
    get_blob_sql = f"""SELECT source_id, data, dtype FROM blobs WHERE source_id = ?"""
    blob = read_from_db(get_blob_sql, [source_id])
    if blob:
        if not os.path.exists(os.path.join(os.getcwd(), 'temp')):
            os.makedirs(os.path.join(os.getcwd(), 'temp'))
        blob = blob[0]
        blob_dtype = blob['dtype']
        file_path = os.path.join(os.getcwd(), 'temp', source_id) 
        try: 
            with open(file_path, 'wb') as f:
                f.write(blob['data'])
            mimetype= MIMETYPES[blob_dtype] 
            return send_file(file_path, mimetype=mimetype)

        except Exception as e:
            return jsonify({'error': 'File not available.'}), 400
    else:
        return jsonify({'error': 'File not found'}), 400

@app.route('/v1/error', methods=['POST'])
def error():
    data = request.json
    logger.info('Error boundary catch error with: %s', data)
    return jsonify({'success': True}), 200

def check_plan(user_id, check='posts'):
    context = default_context(user_id) 
    user_group = context['user_group']
    max_bots = PLANS[user_group]['maxBots']
    max_messages = PLANS[user_group]['maxMessages']
    cur_posts = context['usage']['n_chatbots']
    cur_messages = context['usage']['n_messages']
    if check == 'posts':
        return cur_posts < max_bots
    elif check == 'messages':
        return cur_messages < max_messages
    else:
        return False

@app.route('/v1/source/create', methods=['POST'])
@jwt_auth
def link_source(user_id):

    if not check_plan(user_id, check='posts'):
        return jsonify({'error': 'You have reached the plan limit. Upgrade your plan to add more.'}), 400

    data = request.json
    source_type = data['source_type']

    if source_type == DTYPE_URL:
        try:
            url = data['url']
            res, success = preflight_url_validation_headless(url, user_id)
            if not success: 
                return jsonify({'error': res['error']}), 400 
            source_id = res['source_id']
            write_link_to_temp_sql = f"""INSERT INTO temp_links (user_id, source_id, link_id, url, n_tokens, content) VALUES (?, ?, ?, ?, ?, ?)"""
            entries = [user_id, source_id, res['link_id'], res['url'], res['n_tokens'], res['content']]
            write_to_db(write_link_to_temp_sql, entries)
            source_id = file_queue.add(user_id, fname=url, dtype=DTYPE_URL, source_id=source_id)
        except Exception as e:
            return jsonify({'error': 'Invalid URL'}), 400

    if source_type == DTYPE_VIDEO:
        try:
            print('processing ytvideo with url', data['url'])
            url = data['url']
            res, success = process_youtube_video(url) 
            if not success: 
                return jsonify({'error': res['error']}), 400 
            source_id = res['source_id']
            write_link_to_temp_sql = f"""INSERT INTO temp_links (user_id, source_id, link_id, url, n_tokens, content) VALUES (?, ?, ?, ?, ?, ?)"""
            entries = [user_id, source_id, res['link_id'], res['url'], res['n_tokens'], res['content']]
            write_to_db(write_link_to_temp_sql, entries)
            source_id = file_queue.add(user_id, fname=url, dtype=DTYPE_VIDEO, source_id=source_id)
        except Exception as e:
            print('error with ytvideo', e)
            return jsonify({'error': e}), 400

    return jsonify({'upload_success': True, 'source_id': source_id, 'name': res['name']})


@app.route('/upload', methods=['POST'])
@jwt_auth
def upload(user_id):

    if not check_plan(user_id, check='posts'):
        return jsonify({'error': 'You have reached the plan limit. Upgrade your plan to add more.'}), 200 

    f = request.files.get('inputFile')
    fileType = os.path.splitext(f.filename)[1]
    fileType = fileType.lower().strip('.')
    user_folder = os.path.join(os.getcwd(), 'users', user_id)

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    if not os.path.exists(user_folder+'/files'):
        os.makedirs(user_folder+'/files')

    files_folder = os.path.join(user_folder, 'files')
    fname = secure_filename(f.filename)
    fpath = os.path.join(files_folder, fname)
    f.save(fpath)
    source_id = file_queue.add(user_id, fname, dtype=fileType)
    send_upload_email(email='pablo@upstreamapi.com', user=user_id, title=fname)
    return jsonify({'upload_sucess': True if os.path.exists(fpath) else False, 'source_id': source_id}), 200

@app.route('/v1/source/<source_id>', methods=['GET'])
@jwt_auth
def source(user_id, source_id):
    source_sql = f"""SELECT source_id, status, n_tokens, name FROM data_sources WHERE source_id = ? and user_id = ?"""
    record = read_from_db(source_sql, [source_id, user_id])
    if not record: 
        return jsonify({'status': 'notFound'}), 404
    data = record[0]
    print('\n\n\n', 'Data processed: ', data, '\n\n\n')
    return jsonify({'status': data['status'], 'n_tokens': data['n_tokens'], 'name': data['name'], 'source_id': data['source_id']})

@app.route('/v1/post/<post_id>/reactors', methods=['GET'])
@jwt_auth
def reactors(user_id, post_id):
    try:
        # get reaction counts and if current user has reactred
        get_reaction_sql = f"""SELECT 
                                    reaction, 
                                    count(*) as reaction_cnt,
                                    SUM(CASE WHEN user_id = ? THEN 1 ELSE 0 END) as has_reacted
                               FROM reactions 
                               WHERE bot_id = ? 
                               GROUP BY 1"""

        reactors = read_from_db(get_reaction_sql, [user_id,post_id])
        if reactors:
            likes = reactors[0]
            likes['has_reacted'] = True if likes['has_reacted'] == 1 else False
        else:
            likes = {'reaction': 'like', 'reaction_cnt':0, 'has_reacted': False}
        return jsonify(likes)
    except Exception as e:
        return jsonify({}), 400

@app.route('/v1/post/<post_id>/reactors', methods=['POST'])
@jwt_auth
def react(user_id, post_id):
    data = request.json
    reaction = data.get('reaction', 'like')
    # check if user has already reacted, if so, delete it, else add
    check_reaction_sql = f"""SELECT * FROM reactions WHERE bot_id = ? AND user_id = ?"""
    record = read_from_db(check_reaction_sql, [post_id, user_id])
    try:
        if record:
            delete_reaction_sql = f"""DELETE FROM reactions WHERE bot_id = ? AND user_id = ?"""
            write_to_db(delete_reaction_sql, [post_id, user_id])
        else:
            insert_reaction_sql = f"""INSERT INTO reactions (bot_id, user_id, reaction) VALUES (?, ?, ?)"""
            write_to_db(insert_reaction_sql, [post_id, user_id, reaction])
        return '', 200
    except Exception as e:
        return '', 500

@app.route('/v1/bots/<bot_id>', methods=['GET'])
@app.route('/v1/bots', defaults={'bot_id': None}, methods=['GET'])
@jwt_auth
def bots(user_id, bot_id):
    request_url = request.url
    owner_required = 1 if 'edit' in request_url else 0
    bot_sql = f"""
        SELECT 
            b.bot_id as id, 
            b.name, 
            b.model_id, 
            b.description, 
            b.system_message, 
            b.temperature,
            b.source_id,
            b.created_at,
            b.metadata,
            b.visibility,
            d.name as source_name,
            d.dtype as source_type,
            d.n_tokens as source_n_tokens,
            d.created_at as source_created_at,
            CASE WHEN b.user_id = ? THEN TRUE ELSE FALSE END AS is_owner
        FROM bots b
        JOIN data_sources d ON d.source_id = b.source_id
        WHERE ((CASE WHEN b.user_id = ? THEN 1 ELSE 0 END) = 1
            OR (b.visibility = 'public'))
            AND b.bot_id = ?
            AND CASE WHEN b.user_id = ? THEN 1 ELSE 0 END >= ?
        ORDER BY b.created_at DESC
        """

    bots_sql = f"""
        SELECT 
            b.bot_id as id, 
            b.name, 
            b.model_id, 
            b.description, 
            b.system_message, 
            b.temperature,
            b.source_id,
            b.created_at,
            b.metadata,
            b.visibility,
            d.name as source_name,
            d.dtype as source_type,
            d.n_tokens as source_n_tokens,
            d.created_at as source_created_at,
            CASE WHEN b.user_id = ? THEN TRUE ELSE FALSE END AS is_owner
        FROM bots b
        JOIN data_sources d ON d.source_id = b.source_id
        WHERE b.user_id = ? 
        ORDER BY b.created_at DESC
        """

    bindings = [user_id, user_id, bot_id, user_id, owner_required] if bot_id else [user_id, user_id]
    q = bot_sql if bot_id else bots_sql
    bots = read_from_db(q, bindings)
    
    if not bots:
        return jsonify({'bots': []})

    out_bots = {}

    for bot in bots:
        if bot['id'] not in out_bots:
            out_bots[bot['id']] = {
                'id': bot['id'],
                'name': bot['name'],
                'model_id': bot['model_id'],
                'description': bot['description'],
                'system_message': bot['system_message'],
                'temperature': bot['temperature'],
                'created_at': bot['created_at'],
                'metadata': json.loads(bot['metadata']),
                'sources': [
                    {
                        'source_id': bot['source_id'],
                        'name': bot['source_name'],
                        'dtype': bot['source_type'],
                        'n_tokens': bot['source_n_tokens'],
                        'created_at': bot['source_created_at']
                    }
                ],
                'visibility': bot['visibility']
            }

        else:
            out_bots[bot['id']]['sources'].append({
                'source_id': bot['source_id'],
                'name': bot['source_name'],
                'dtype': bot['source_type'],
                'n_tokens': bot['source_n_tokens'],
                'created_at': bot['source_created_at']
            })

    return jsonify({'bots': list(out_bots.values())})


@app.route('/v1/bot/new', methods=['POST'])
@jwt_auth
def new_bot(user_id):
    data = request.json
    bot_name = data.get('name', None)
    bot_description = data.get('description', None)
    sources = data.get('sources', [])
    model_id = data.get('model_id', None)
    system_message = data['system_message']
    temperature = data.get('temperature', None)
    metadata = data.get('metadata', None)
    visibility = data.get('visibility', 'private')

    if isinstance(metadata, dict):
        metadata = json.dumps(metadata)
    else:
        metadata = '{}'

    bot_id = 'bot_'+generate_uuid(8)

    entries = [(bot_id, user_id, bot_name, bot_description,
                source_id, model_id, system_message, temperature, metadata, visibility) for source_id in sources] if sources else [(bot_id, user_id, bot_name, bot_description, EMPTY_STRING, model_id, system_message, temperature, metadata, visibility)]
    bots_new_sql = f"""INSERT INTO bots (bot_id, user_id, name, description, source_id, model_id, system_message, temperature, metadata, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    try:
        sql_upsert_n_bot = f'INSERT INTO usage (user_id, n_chatbots, n_sources, n_tokens, n_messages) VALUES (?, 1, 0, 0, 0) ON CONFLICT(user_id) DO UPDATE SET n_chatbots = n_chatbots + 1;'
        write_to_db(sql_upsert_n_bot, [user_id])

    except Exception as e:
        logger.error('Error updating usage table')

    try:
        write_many_to_db(bots_new_sql, entries)
        bot = {
            'id': bot_id,
            'name': bot_name,
            'description': bot_description,
            'sources': [source_id for source_id in sources] if sources else [],
            'model_id': model_id,
            'system_message': system_message,
            'temperature': temperature,
            'metadata': json.loads(metadata),
            'visibility': visibility 
        }
        return jsonify({'bot': bot}), 200

    except Exception as e:
        logger.error(e)
        return jsonify({'error': 'error'}), 500


@app.route('/v1/bot/<bot_id>', methods=['DELETE'])
@jwt_auth
def delete_bot(user_id, bot_id):
    bot_delete_sql = f"""DELETE FROM bots WHERE bot_id = ? and user_id = ?"""

    try:
        sql_upsert_n_bot = f'INSERT INTO usage (user_id, n_chatbots, n_sources, n_tokens, n_messages) VALUES (?, 0, 0, 0, 0) ON CONFLICT(user_id) DO UPDATE SET n_chatbots = n_chatbots - 1;'
        write_to_db(bot_delete_sql, [bot_id, user_id])
        write_to_db(sql_upsert_n_bot, [user_id])

    except Exception as e:
        logger.error(e)

    return jsonify({'success': True}), 200


@app.route('/v1/bot/<bot_id>', methods=['PATCH'])
@jwt_auth
def update_bot(user_id, bot_id):
    data = request.json
    bot_name = data.get('name', None)
    bot_description = data.get('description', None)
    sources = data.get('sources', [])
    model_id = data.get('model_id', None)
    temperature = data.get('temperature')
    system_message = data.get('system_message')
    metadata = data.get('metadata', None)
    visibility = data.get('visibility', None)

    source_id = sources[0] if sources else None 

    if not source:
        return jsonify({'error': 'Assistant without source'}), 400

    if isinstance(metadata, dict):
        metadata = json.dumps(metadata)

    else:
        metadata = '{}'

    try:
        bot_update_sql = """
        UPDATE bots 
        SET name = ?, description = ?, source_id = ?, model_id = ?, system_message = ?, temperature = ?, metadata = ?, visibility = ?
        WHERE bot_id = ? and user_id = ?
        """

        write_to_db(bot_update_sql, [bot_name, bot_description, source_id, model_id, system_message, temperature, metadata, visibility, bot_id, user_id])

        bot = {
            'id': bot_id,
            'user': user_id,
            'name': bot_name,
            'description': bot_description,
            'sources': [source_id],
            'model_id': model_id,
            'system_message': system_message,
            'temperature': temperature,
            'metadata': json.loads(metadata),
            'visibility': visibility
        }

        response = jsonify({'bot': bot}), 200
        return response

    except Exception as e:
        logger.error(e)
        response = jsonify({'error': 'error'}), 500
        return response

class InferenceError(Exception):
    pass


# @app.route('/v1/search', methods=['POST'])
# @jwt_auth
# def search(user_id):
#     import json
#     from embeddings import compute_distances, read_embeddings_from_db
#     data = request.json
#     sources_ids = [s['source_id'] for s in data['sources']] if data['sources'] else []
#     data['messages'] = []
#     try:
#         d_embeddings_df = read_embeddings_from_db(sources_ids)
#         q_embeddings = get_q_embeddings(q=data['query'])
#         d_embeddings_df = compute_distances(d_embeddings_df, q_embeddings)
#         sources = fetch_passages(d_embeddings_df, max_passages=5)
#         if not sources:
#             return jsonify({'summary': 'Couldn\'t find relevant information.', 
#                             'facts': {}, 
#                             'reference': {'id': '', 'title': '', 'text': '', 'score': '', 'n_tokens': ''}}), 200

#         data['context'] = '###'.join([s['text'] for s in sources])

#         data['context'] = data['context'] + '\n' + \
#             '\n Example response \n' + get_few_shot_loop_json() + \
#             '\n Make sure the response can be parsed by Python json.loads and only fill in the same key value pairs, if not present, show the key and leave the value empty.'

#         chat_inputs = DataLoader.construct_chat(data, api_key='')
#         chat_inputs.add_user_message(data["query"])
#         messages = chat_inputs.get_messages('facts')
#         response, success = chat_completion( model=MODEL_MAP[chat_inputs.model_id], messages=messages, temp=1)
#         if not success: raise InferenceError()

#         message = response.get('choices', [{}])[0].message
#         content = message['content'].strip()

#         data = json.loads(content)

#         print('\n\n\nRESPONSE:', json.dumps(data, indent=4), '\n\n\n')

#         if validate_format(content):
#             d = json.loads(content)
#             out = {'summary': '', 'facts': flatten_json(d['facts']), 'reference': sources[0]}
#             return jsonify(out), 200

#         else:
#             logger.error('\n\n\n\n INVALID FORMAT \n\n\n\n\n')
#             return jsonify({'summary': 'Couldn\'t find relevant information. Try again.', 'facts': {}, 'reference': {'id': '', 'title': '', 'text': '', 'score': '', 'n_tokens': ''}}), 200

#     except Exception as e:
#         logger.error(f'\n\n\n\n EXCEPTION: {e} \n\n\n\n\n')
#         return jsonify({'summary': 'Couldn\'t find relevant information. Please try again.', 'facts': {}, 'reference': {'id': '', 'title': '', 'text': '', 'score': '', 'n_tokens': ''}}), 200

@app.route('/v1/search', methods=['POST'])
@jwt_auth
def search(user_id):
    import json
    from embeddings import read_embeddings_from_db

    data = request.json
    sources_ids = [s['source_id'] for s in data['sources']] if data['sources'] else []
    data['messages'] = []

    try: 
        d_embeddings_df = read_embeddings_from_db(sources_ids)        
        sources = fetch_passages(d_embeddings_df, max_passages=1000, sort_by='id', ascending=True)

    except Exception as e:
        print('Error fetching passages', e)
        return jsonify(''), 500

    choices = []

    for s in sources:
        for category in ['emptyfacts']:
            data['context'] = get_few_shot_loop_json(category) + \
                'Text:\n\n' + s['text'] + \
                    '\n Please follow these instructions with extreme care: \n\
                    Make sure the response can be parsed by Python json.loads \n\
                    Fill in exactly the same keys as shown below, do not add or remove keys.\n\
                    If the information is not present, show the key and leave the value empty.\n\
                    Only respond with the JSON, no commentary.\n'
            chat_inputs = DataLoader.construct_chat(data, api_key='')
            chat_inputs.add_user_message(data["query"])
            messages = chat_inputs.get_messages('facts')
        
            try: 
                response, success = chat_completion(model=MODEL_MAP[chat_inputs.model_id], messages=messages, temp=0.5)
                if not success: 
                    raise InferenceError()
            except Exception as e:
                logger.error(f'\n\n\n\n EXCEPTION: {e} \n\n\n\n\n')

            message = response.get('choices', [{}])[0].message
            content = message['content'].strip()

            try: 
                if validate_format(content):
                    d_out = json.loads(content)
                    # d_out = flatten_json(d)
                    choices.append(d_out)
                else:
                    print('\n\n\n\n INVALID FORMAT \n\n\n\n\n', content)
            except Exception as e:
                print('Error validating format', e)
                pass

    # For all key-value pairs, consolidate the values into a list
    d_out = {}
    for d in choices:
        for k, v in d.items():
            k = k.lower()   
            if k not in d_out:
                d_out[k] = []
            d_out[k].append(v)
    # d_out = <key: [value1, value2, ...], ...>

    return jsonify({'facts': d_out}), 200

@app.route('/v1/inference', methods=['POST'])
@jwt_auth
def stream_v1(user_id):
    # This allows for demo, logic is odd though
    if user_id == 'anon':
        pass
    else:
        if not check_plan(user_id, check='messages'):
            return jsonify({'error': 'You have reached your plan limit. Upgrade your plan to continue.'}), 402
    data = request.json
    data['conversation_id'] = data['conversation_id'] if data['conversation_id'] else generate_uuid()
    sources_ids = [s['source_id'] for s in data["sources"]] if data["sources"] else []

    if sources_ids:
        d_embeddings_df = read_embeddings_from_db(sources_ids)
        if d_embeddings_df is not None:
            from embeddings import compute_distances
            q_embeddings = get_q_embeddings(q=data['user_message'])
            d_embeddings_df = compute_distances(d_embeddings_df, q_embeddings)
            refs = create_context(d_embeddings_df, max_len=7000 if user_id in USERS_WITH_GPT4 else 3000,
                                  max_passages=100 if user_id == USERS_WITH_GPT4 else 8)
            ls = ['{}: {}'.format(ref['title'], ref['text']) for ref in refs]
            s = '###'.join(ls)
            data['context'] = s
    else:
        data['context'] = ''
        refs = []

    try:
        chat_inputs = DataLoader.construct_chat(data, api_key='sk-123')
        print(chat_inputs)
        user_message_id = chat_inputs.user_message_id
        user_message = chat_inputs.user_message
        messages = chat_inputs.get_messages()

    except Exception as e:
        return jsonify({'error': 'Something went wrong. Please retry.'}), 500

    response, success = chat_completion(model='gpt-4' if user_id in USERS_WITH_GPT4 else MODEL_MAP[chat_inputs.model_id], messages=messages, temp=chat_inputs.temperature, stream=TEST_STREAM)

    if not success: 
        return jsonify({'error': 'Something went wrong. Please retry.'}), 500

    def generate(user_message, user_message_id, chat_inputs):
        content = ''
        try: 
            for e in response:
                stop = e['choices'][0]['finish_reason']
                content += e['choices'][0]['delta'].get('content','')
                if stop == 'stop': 
                    try:
                        # Save to db
                        insert_message_sql = f"""INSERT INTO chat (user_id, role, content, message_id, conversation_id, chatbot_id) VALUES (?, ?, ?, ?, ?, ?)"""
                        user_message = [user_id, 'user', user_message, user_message_id, chat_inputs.conversation_id, chat_inputs.chatbot_id]
                        assistant_message = [user_id, 'assistant', content, user_message_id+1, chat_inputs.conversation_id, chat_inputs.chatbot_id]
                        write_to_db(insert_message_sql, user_message)
                        write_to_db(insert_message_sql, assistant_message)
                        sql_upsert_messages = f'INSERT INTO usage (user_id, n_chatbots, n_sources, n_tokens, n_messages) VALUES (?, 0, 0, 0, 1) ON CONFLICT(user_id) DO UPDATE SET n_messages = n_messages + 1;'
                        write_to_db(sql_upsert_messages, [user_id])
                        logger.info(f'Saved last message to db')
                    except Exception as e:
                        logger.error(f'Error saving last message to db with: {e}')

                res = {'content': content, 'message_id': user_message_id+1, 'conversation_id': chat_inputs.conversation_id, 'refs' : refs, 'finish': stop is not None }
                yield 'data: ' + json.dumps(res) + '\n\n'

        except GeneratorExit:
            logger.info('Generator exited ')
        
    return Response(generate(user_message,user_message_id, chat_inputs), mimetype='text/event-stream')

@app.route('/v1/conversation/<conversation_id>', methods=['GET'])
@jwt_auth
def chat(user_id, conversation_id):
    # TODO: Add PATCH is_visible so users can delete conversations
    conversation_id_sql = f"""SELECT * FROM chat WHERE conversation_id = ? and user = ? ORDER BY message_id ASC"""
    conversation = read_from_db(conversation_id_sql, [conversation_id, user_id])

    messages = []
    for conv in conversation:
        messages.append({
            'id': conv.get('message_id', None),
            'role': conv.get('role', None),
            'content': conv.get('content', None)
        })

    # get latest bot used
    bot_id = conversation[-1]['chatbot_id']
    return jsonify({'messages': messages, 'conversationId': conversation_id, "botId": bot_id})


@app.route('/v1/account', methods=['GET'])
@jwt_auth
def check_registration(user_id, **kwargs):
    email = kwargs['email']
    sql_check_user = f"""SELECT * FROM users WHERE user_id = ?"""
    r = read_from_db(sql_check_user, [user_id])
    if r: 
        return '', 200

    try:
        entry = [user_id, email]
        sql_register = f"""INSERT INTO users (user_id, email) VALUES (?, ?)"""
        write_to_db(sql_register, entry)

        sql_register_usage = f"""INSERT INTO usage (user_id, n_chatbots, n_sources, n_tokens, n_messages) VALUES (?, ?, ?, ?, ?)"""
        usage_entry = [user_id, 0, 0, 0, 0]
        write_to_db(sql_register_usage, usage_entry)
        return '', 200
    
    except Exception as e:
        logger.error(f'Error registering user with: {e}')
        return '', 500

@app.route('/v1/usage', methods=['GET'])
@jwt_auth
def usage(user_id):
    try:
        context = default_context(user_id)
        return jsonify({'usage': context['usage'], 'user_group': context['user_group']})

    except Exception as e:
        logger.error(f'Error getting usage with: {e}')
        return jsonify({'usage': None, 'account': None}),404

@app.route('/privacy', methods=['GET'])
def privacy():
    return render_template('privacy.html')


@app.route('/webhook', methods=['POST'])
def webhook():

    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY") 
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

    # id to user_group product map 
    PRODUCTS_MAP = {'prod_NMAjKSoxmEWAXQ' : 'pro', 
                    'prod_O0KvklwUWF7w4j': 'basic', 
                    }
    
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)

    except ValueError as e:
        raise e

    except stripe.error.SignatureVerificationError as e:
        raise e

    # Handle session of completed events to fulfill orders
    if event['type'] == 'checkout.session.completed':
        session = stripe.checkout.Session.retrieve(event['data']['object']['id'], expand=['customer', 'line_items'])
        customer_email = session.customer.email if session.customer else session['customer_details']['email']
        product_id = session.line_items.data[0].price.product
        product_name = PRODUCTS_MAP[product_id]
        logger.info(f'Checkout session completed:\n email: {customer_email} \n product id: {product_id} \n product: {product_name}')
        try:
            user_group = PRODUCTS_MAP[product_id]
            new_sk = generate_uuid()
            user_upsert_sql = f'INSERT INTO users (email, sk, user_group) VALUES (?,?,?) ON CONFLICT(email) DO UPDATE SET user_group = ?;'
            write_to_db(user_upsert_sql, [customer_email, new_sk, user_group, user_group])
        except Exception as e:
            logger.error(f'Error updating purchase {customer_email} with: {e}')
        try:
            get_user_sql = f"""SELECT email, sk, user_group FROM users WHERE email = ?"""
            user = read_from_db(get_user_sql, [customer_email])[0]
            customer_email = user['email']
            message = Mail(from_email=From('hi@upstreamapi.com', 'Upstream AI'), to_emails=[To(customer_email), Bcc('hi@upstreamapi.com')], subject=f'Your subscription for Upstream {user_group.upper()} been paid!', html_content=fill_html('templates/purchase_email.html', **{'email': customer_email, 'user_group': user_group.upper()}))
            sg = SendGridAPIClient(SG_API_KEY)
            sg.send(message)
        except Exception as e:
            logger.error(f'Error sending payment email for {customer_email} with: {e}')
    
    elif event['type'] == 'customer.subscription.deleted':
        sub = stripe.Subscription.retrieve(event['data']['object']['id'], expand=['customer'])
        customer_email = sub['customer']['email']
        try:
            user_update_sql = f'UPDATE users SET user_group = "free" WHERE email = ?'
            write_to_db(user_update_sql, [customer_email])
        except Exception as e:
            logger.error(f'Error cancelling {customer_email} subscription with: {e}')
    else:
        logger.info('Unhandled event type {}'.format(event['type']))
    return jsonify(success=True)

def default_context(user_id):
    context = {}
    user_sql = f"""SELECT 
                    u.user_id, 
                    u.user_group, 
                    u.created_at,
                    COALESCE(usage.n_messages, 0) as n_messages,
                    COALESCE(usage.n_chatbots, 0) as n_chatbots,
                    COALESCE(usage.n_sources, 0) as n_sources, 
                    COALESCE(usage.n_tokens, 0) as n_tokens
                FROM users u 
                LEFT JOIN usage ON u.user_id = usage.user_id
                WHERE u.user_id = ?"""
    user = read_from_db(user_sql, [user_id])
    try:
        user = user[0]
    except Exception as e: 
        raise e

    context['user_id'] = user['user_id']
    context['user_group'] = user['user_group']
    context['created_at'] = user['created_at']
    context['usage'] = {
        'n_messages': user['n_messages'],
        'n_chatbots': user['n_chatbots'],
        'n_sources': user['n_sources'],
        'n_tokens': user['n_tokens'],
        'user_id': user['user_id']
    }
    return context