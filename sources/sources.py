from . import sources_bp
from extra.auth import jwt_auth
from flask import jsonify
from db import read_from_db
from extra.utils import read_query

@sources_bp.route('/v1/source/<source_id>', methods=['GET'])
@jwt_auth
def source(user_id, source_id):
    sourceq = read_query('source')
    record = read_from_db(sourceq, [source_id, user_id])

    if not record: 
        return jsonify({'status': 'notFound'}), 404

    data = record[0]

    return jsonify({'status': data['status'], 
                    'n_tokens': data['n_tokens'], 
                    'name': data['name'], 
                    'source_id': data['source_id']})
