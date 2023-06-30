from flask import Blueprint

core_bp = Blueprint('core', __name__, url_prefix='/')

from . import core 
from . import error