from flask import Flask, render_template, redirect
from dotenv import load_dotenv
from db import create_store
from constants import MAX_FILE_SIZE
from flask_cors import CORS
from taskqueue import FileQueue
from resources import resources_bp
from core import core_bp
from user import user_bp
import os

from extra.logger_config import setup_logger
logger = setup_logger(__name__)
load_dotenv()

create_store()
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE 
app.secret_key = os.getenv("SECRET_KEY")
app.config['file_queue'] = FileQueue()
CORS(app)

app.register_blueprint(resources_bp)
app.register_blueprint(core_bp)
app.register_blueprint(user_bp)

@app.before_first_request
def before_first_request():
    app.config['file_queue'].start_processing()

@app.errorhandler(408)
@app.errorhandler(404)
@app.errorhandler(400)
def page_not_found(_):
    return render_template('404.html')

@app.route('/')
def index(): return redirect("https://autodocai.com", code=302)
