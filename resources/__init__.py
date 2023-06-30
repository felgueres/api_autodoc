from flask import Blueprint

resources_bp = Blueprint('resources', __name__, url_prefix='/')

from . import sources
from . import files
from . import templates 
from . import documents 