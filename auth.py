from flask import request
from typing import Dict
from functools import wraps
from db_utils import read_from_db
INVALID_AUTH_MSG = "Invalid authentication."
import os
from constants import DEMO_USER
from dotenv import load_dotenv

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

def get_token_auth_header() -> str:
    """Obtains the access token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)

    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                         "description":
                             "Authorization header is expected"}, 401)
    parts = auth.split()
    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must start with"
                            " Bearer"}, 401)
    if len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    if len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                         "description":
                             "Authorization header must be"
                             " Bearer token"}, 401)
    token = parts[1]
    return token

def verify_auth_token(token: str) -> str:
    """Verifies the access token
    """
    is_valid_user_sql = f"SELECT * FROM users WHERE sk = ?"
    valid_user = read_from_db(is_valid_user_sql, [token])
    return True if valid_user else False 

def verify_public_token(token: str) -> str:
    """Verifies the access token
    """
    is_valid_user_sql = f"SELECT * FROM embeds WHERE embed_id = ?"
    valid_user = read_from_db(is_valid_user_sql, [token])
    return True if valid_user else False

def requires_public_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        if token.startswith('pk-'):
            parts = token.split('pk-') # pk- is for public keys, eg. embed ids, etc.
            if len(parts) == 1 or len(parts)>2:
                raise AuthError({"code": "invalid_key","description":INVALID_AUTH_MSG}, 401)  
            else:
                key = parts[1]
                if verify_public_token(key):
                    return f(*args, **kwargs)
                else:
                    raise AuthError({"code": "invalid_key","description":INVALID_AUTH_MSG}, 401)
        else:
            raise AuthError({"code": "invalid_key","description":INVALID_AUTH_MSG}, 401)

    return decorated


def requires_auth(f):
    """Decorator to add auth to endpoints. 
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        if token.startswith('sk-'):
            parts = token.split('sk-')
            if len(parts) == 1 or len(parts)>2:
                raise AuthError({"code": "invalid_key","description":"Get your keys from upstreamapi.com"}, 401)  
            else:
                key = parts[1]
                if verify_auth_token(key):
                    return f(*args, **kwargs)
                else:
                    raise AuthError({"code": "invalid_key","description":INVALID_AUTH_MSG}, 401)
        else:
            raise AuthError({"code": "invalid_key","description":INVALID_AUTH_MSG}, 401)

    return decorated

def jwt_auth(f):
    from jwt import decode
    @wraps(f)
    def wrap(*args, **kwargs):
        
        try:
            token = request.headers.get('Authorization', '').split('Bearer ')[-1]

        except Exception:
            raise AuthError({"code": "no_key","description":"Get your keys from upstreamapi.com"}, 401)

        if not token:
            raise AuthError({"code": "no_key","description":"Get your keys from upstreamapi.com"}, 401)  
        
        try:
            decoded = decode(token, SUPABASE_SECRET, algorithms=["HS256"], audience=["authenticated"])
            user_id = decoded['sub']
        except Exception:
            raise AuthError({"code": "invalid_key","description":"Get your keys from upstreamapi.com"}, 401)

        if f.__name__ == 'check_registration':
            email = decoded['email']
            return f(*args, **kwargs, user_id=user_id, email=email)
        else:
            return f(*args, **kwargs, user_id=user_id)
        
    return wrap
