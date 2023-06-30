from . import user_bp
from extra.auth import jwt_auth
from extra.utils import read_query
from db import read_from_db, write_to_db
from flask import jsonify
from constants import PLANS
from extra.logger_config import setup_logger
import os

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

logger = setup_logger(__name__)

@user_bp.route('/v1/account', methods=['GET'])
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

@user_bp.route('/v1/usage', methods=['GET'])
@jwt_auth
def usage(user_id):
    try:
        context = default_context(user_id)
        return jsonify({'usage': context['usage'], 'user_group': context['user_group']})
    except Exception as e:
        logger.error(f'Error getting usage with: {e}')
        return jsonify({'usage': None, 'account': None}),404

def default_context(user_id):
    context = {}
    contextq = read_query("user_context") 
    user = read_from_db(contextq, [user_id])
    user = user[0]
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