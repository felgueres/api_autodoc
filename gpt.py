import os
import openai
import backoff
from dotenv import load_dotenv

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_KEY")
if OPENAI_KEY:
    openai.api_key = OPENAI_KEY
else:
    print('OpenAI key not set')

class RetriableError(Exception):
    pass

class FatalError(Exception):
    pass

retriable_exceptions = (openai.error.APIError, openai.error.Timeout, openai.error.RateLimitError)

def non_retriable(e):
    return not isinstance(e, retriable_exceptions)

@backoff.on_exception(backoff.expo, openai.error.OpenAIError, max_tries=5)
def completions_with_backoff(**kwargs):
    return openai.ChatCompletion.create(**kwargs, request_timeout=12)

def gpt(prompt, functions, model='gpt-3.5-turbo-0613', temperature=0.5, max_tokens=1000, n=1, stop=None):
    messages = [{'role': 'user', 'content': prompt}]
    res = completions_with_backoff(messages=messages, functions=functions, model=model, temperature=temperature, max_tokens=max_tokens, n=n, stop=stop)
    return res