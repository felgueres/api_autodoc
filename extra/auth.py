from flask import request
from typing import Dict
from functools import wraps
import os
from dotenv import load_dotenv
INVALID_AUTH_MSG = "Invalid authentication."

load_dotenv()
SUPABASE_SECRET = os.getenv("SUPABASE_SECRET")

class AuthError(Exception):
    """
    An AuthError is raised whenever the authentication failed.
    """
    def __init__(self, error: Dict[str, str], status_code: int):
        super().__init__()
        self.error = error
        self.status_code = status_code

def jwt_auth(f):
    from jwt import decode
    @wraps(f)
    def wrap(*args, **kwargs):
        
        try:
            token = request.headers.get('Authorization', '').split('Bearer ')[-1]

        except Exception:
            raise AuthError({"code": "no_key","description":INVALID_AUTH_MSG}, 401)

        if not token:
            raise AuthError({"code": "no_key","description":INVALID_AUTH_MSG}, 401)  
        
        try:
            decoded = decode(token, SUPABASE_SECRET, algorithms=["HS256"], audience=["authenticated"])
            user_id = decoded['sub']
        except Exception:
            raise AuthError({"code": "invalid_key","description":INVALID_AUTH_MSG}, 401)

        if f.__name__ == 'check_registration':
            email = decoded['email']
            return f(*args, **kwargs, user_id=user_id, email=email)
        else:
            return f(*args, **kwargs, user_id=user_id)
        
    return wrap
