from . import resources_bp
import os
from flask import jsonify, send_file
from extra.utils import read_query
from extra.auth import jwt_auth
from constants import MIMETYPES
from db import read_from_db
from flask import request, current_app
from werkzeug.utils import secure_filename
from extra.send_email import send_upload_email
SG_API_KEY = os.getenv("SG_API_KEY")

@resources_bp.route('/v1/file/upload', methods=['POST'])
@jwt_auth
def upload(user_id):
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

    source_id = current_app.config['file_queue'].add(user_id, fname, dtype=fileType)
    send_upload_email(email='pablo@upstreamapi.com', user=user_id, title=fname)
    return jsonify({'upload_sucess': True if os.path.exists(fpath) else False, 'source_id': source_id}), 200

@resources_bp.route('/v1/file/<source_id>', methods=['GET'])
@jwt_auth
def get_file(user_id, source_id):
    try:
        blob = read_from_db(read_query('blob'), [source_id])
        if not os.path.exists(os.path.join(os.getcwd(), 'temp')):
            os.makedirs(os.path.join(os.getcwd(), 'temp'))
        blob = blob[0]
        blob_dtype = blob['dtype']
        file_path = os.path.join(os.getcwd(), 'temp', source_id) 

        with open(file_path, 'wb') as f:
            f.write(blob['data'])
            mimetype= MIMETYPES[blob_dtype] 
            return send_file(file_path, mimetype=mimetype)

    except Exception as e:
        return jsonify({'error': 'File not found'}), 400
