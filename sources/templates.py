from . import sources_bp
from extra.auth import jwt_auth
from flask import jsonify, request
from extra.utils import generate_uuid
import json
from db import read_from_db, write_to_db

from extra.logger_config import setup_logger
logger = setup_logger(__name__)

@sources_bp.route('/v1/template/new', methods=['POST'])
@jwt_auth
def new_template(user_id):
    data = request.json
    template_id = 't_'+generate_uuid(8)
    try:
        fields = data['fields']
        name = data['name']
        description = data['description']
        fields = json.dumps(fields)
    except Exception:
        return '', 400 
    try:
        template_new_sql = f"""INSERT INTO templates (template_id, user_id, name, description, fields) VALUES (?, ?, ?, ?, ?)"""
        write_to_db(template_new_sql, [template_id, user_id, name, description, fields])
    except Exception:
        return '', 500
    return jsonify({'template_id': template_id}), 200 

@sources_bp.route('/v1/templates/<template_id>', methods=['PATCH'])
@jwt_auth
def update_template(user_id, template_id):
    data = request.json
    try:
        fields = data['fields']
        name = data['name']
        description = data['description']
        fields = json.dumps(fields)
    except Exception:
        return '', 400 

    try:
        print(template_id, user_id, name, description, fields)
        template_update_sql = f"""UPDATE templates SET name = ?, description = ?, fields = ? WHERE template_id = ? and user_id = ?"""
        write_to_db(template_update_sql, [name, description, fields, template_id, user_id])
        return jsonify({'template_id': template_id}), 200

    except Exception:
        return '', 500

@sources_bp.route('/v1/templates/<template_id>', methods=['DELETE'])
@jwt_auth
def delete_template(user_id, template_id):
    bot_delete_sql = f"""DELETE FROM templates WHERE template_id = ? and user_id = ?"""
    try:
        write_to_db(bot_delete_sql, [template_id, user_id])
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({'success': False}), 200

@sources_bp.route('/v1/templates/<template_id>', methods=['GET'])
@sources_bp.route('/v1/templates', defaults={'template_id': None}, methods=['GET'])
@jwt_auth
def get_templates(user_id, template_id):
    if template_id:
        template_sql = f"""
            SELECT 
                t.template_id, 
                t.name,
                t.description,
                t.fields,
                t.created_at
            FROM templates t 
            WHERE t.user_id = ? AND t.template_id = ?
            ORDER BY t.created_at DESC
            """
    else:
        template_sql = f"""
            SELECT 
                t.template_id, 
                t.name,
                t.description,
                t.fields,
                t.created_at
            FROM templates t 
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
            """
    try:
        bindings = [user_id, template_id] if template_id else [user_id]
        templates = read_from_db(template_sql, bindings)
        if not templates:
            return jsonify({'templates': []}), 200
        else:
            for template in templates:
                template['fields'] = json.loads(template['fields'])
            return jsonify({'templates': templates}), 200

    except Exception as e:
        return '', 500