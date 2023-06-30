from flask import Blueprint

sources_bp = Blueprint('sources', __name__, url_prefix='/')

from . import sources
from . import files
from . import templates 