from . import resources_bp
from extra.auth import jwt_auth
from extra.utils import generate_uuid, read_query
from flask import jsonify, request
from db import read_from_db, write_to_db, write_many_to_db
import json
from extra.logger_config import setup_logger
logger = setup_logger(__name__)

@resources_bp.route('/v1/bots/<bot_id>', methods=['GET'])
@resources_bp.route('/v1/bots', defaults={'bot_id': None}, methods=['GET'])
@jwt_auth
def bots(user_id, bot_id):
    request_url = request.url
    owner_required = 1 if 'edit' in request_url else 0

    bot_sql = read_query('bot')
    bots_sql = read_query('bots')

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

@resources_bp.route('/v1/bot/new', methods=['POST'])
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

    bot_id = 'doc_'+generate_uuid(8)

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


@resources_bp.route('/v1/bot/<bot_id>', methods=['DELETE'])
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


@resources_bp.route('/v1/bot/<bot_id>', methods=['PATCH'])
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

    if not source_id:
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
