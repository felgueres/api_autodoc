from . import core_bp
from flask import jsonify, request
from extra.logger_config import setup_logger
logger = setup_logger(__name__)

@core_bp.route('/v1/error', methods=['POST'])
def error():
    data = request.json
    logger.info('Error boundary catch error with: %s', data)
    return jsonify({'success': True}), 200