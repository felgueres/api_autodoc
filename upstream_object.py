import json
import six
import datetime
from jinja2 import Template

DAVINCI_MAX_REQUEST = 4000 
MAX_RESPONSE = 200 # ~2 tweets 
MAX_REQUEST = DAVINCI_MAX_REQUEST - MAX_RESPONSE

class UpstreamObject(dict):
    def __init__(self, id=None, api_key=None, upstream_version=None, **params):
        super(UpstreamObject, self).__init__()
        object.__setattr__(self, "api_key", api_key)
        object.__setattr__(self, "upstream_version", upstream_version)
        if id:
            self["id"] = id
    
    def __setattr__(self, k, v):
        if k[0] == "_" or k in self.__dict__:
            return super(UpstreamObject, self).__setattr__(k, v)
        self[k] = v
        return None

    def __getattr__(self, k):
        if k[0] == "_":
            raise AttributeError(k)
        try:
            return self[k]
        except KeyError as err:
            raise AttributeError(*err.args)

    @classmethod
    def construct_from(cls, values, api_key, upstream_version=None):
        instance = cls(values.get('id'), api_key=api_key, upstream_version=upstream_version)
        instance.refresh_from(values, api_key=api_key, upstream_version=upstream_version)
        return instance

    def refresh_from(self, values, api_key=None, upstream_version=None):
        self.api_key = api_key or getattr(values, "api_key", None)
        self.upstream_version = upstream_version or getattr(values, "upstream_version", None)
        for k, v in six.iteritems(values):
            super(UpstreamObject, self).__setitem__(k, v)

    def __str__(self):
        return json.dumps(self, indent=2)

    @property
    def upstream_id(self):
        return self.id

class DataLoader(object):
    @staticmethod
    def construct_chat(data, api_key):
        chat = Chat.construct_from(data, api_key)
        return chat 

MAX_CONTEXT = 2500 
    
class Chat(UpstreamObject):
    def __init__(self, id=None, api_key=None, upstream_version=None, messages=None):
        self.created_at = datetime.datetime.now().date().strftime("%Y-%m-%d")
    
    def add_system_message(self, mode='chat'):
        if mode == 'chat':
            base_msg = "You are a helpful assistant designed to answer questions about a given document."
            system_msg = Template(base_msg).render({'created_at': self.created_at, 'model_id': self.model_id}) 
        elif mode == 'facts':
            system_msg = "You are an expert analyst that extracts key-value pairs from documents."
        return system_msg

    def get_messages(self, mode='chat'):
        if self.get('system_message', None):
            self.messages.insert(0, {'content': self.system_message, 'role': 'system'})
        else:
            self.messages.insert(0, {'content': self.add_system_message(mode), 'role': 'system'})
        self.compile()
        messages = [{'content': m['content'], 'role': m['role']} for m in self.messages]
        messages[-1]['content'] = self.compiled_message['content']
        return messages 
    
    def add_user_message(self, message):
        self.messages.append({'content': message, 'role': 'user'})
        return None

    def compile(self):
        # Join all messages into one string including role and content
        MESSAGE_TEMPLATE = "{{search_results}} {{user_message}}"
        # SEARCH_RESULTS = """{% if context | length -%} Given the following extracted parts of a long document and a question, create a final answer. If you don't know the answer, just say that you don't know. Don't try to make up an answer.\n\nContent: {{context}}\n\n Question: {%endif%}"""
        SEARCH_RESULTS_EXTRACT = """{% if context | length -%} Given the following text of a document, extract the values for the given set of keys. \n\nKeys: {{context}}\n\n {%endif%}"""
        USER_MESSAGE = """{{user_message}} \n Helpful answer:"""
        str_messages = '\n'.join([f"{m['role']}: {m['content']}" for m in self.messages])
        base_tokens = InferenceUtils.num_tokens_from_string(str_messages)
        context_tokens = int(MAX_REQUEST - base_tokens)
        trunc_context = InferenceUtils.index_n_tokens(self.context, context_tokens)
        # rendered_search_results = Template(SEARCH_RESULTS).render({'context': trunc_context})
        rendered_search_results = Template(SEARCH_RESULTS_EXTRACT).render({'context': trunc_context})
        last_message = self.messages[-1]
        rendered_user_message = Template(USER_MESSAGE).render({'user_message': last_message['content']})
        # Add context to the last message
        compiled_content = Template(MESSAGE_TEMPLATE).render(search_results=rendered_search_results, user_message=rendered_user_message)
        self.compiled_message = {'content': compiled_content, 'role': 'user'}
        return None

class InferenceUtils(object):
    def __init__(self):
        pass

    @staticmethod
    def num_tokens_from_string(string: str) -> int:
        enc = InferenceUtils.get_encoder() 
        return len(enc.encode(string))
    
    @staticmethod
    def get_encoder(encoding_name='gpt2'):
        import tiktoken
        enc = tiktoken.get_encoding(encoding_name)
        return enc
    
    @staticmethod
    def index_n_tokens(string: str, n_tokens= int) -> str:
        enc = InferenceUtils.get_encoder()
        enc_tokens = enc.encode(string)[:n_tokens]
        return enc.decode(enc_tokens)

