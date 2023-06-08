import openai
from time import sleep
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_KEY")

MAX_RETRY = 3
GPT3_MODEL = 'gpt-3.5-turbo'
GPT4_MODEL = 'gpt-4'
GPT3_ID = 'gpt3'
GPT4_ID = 'gpt4'
MODEL_MAP = { GPT3_ID: GPT3_MODEL, GPT4_ID: GPT4_MODEL }

from logger_config import setup_logger
logger = setup_logger(__name__)
import time

def chat_completion(messages, model=GPT3_MODEL, temp=0.25, top_p=1.0, max_tokens=800, freq_pen=0.25, pres_pen=0.0, stop=['<<END>>'], stream=False):
    logger.debug(f"Starttime chat completion: {time.time()}")
    retry_count = 0

    while True:
        try:
            logger.debug(f"Current retry count: {retry_count}")
            openai.api_key = OPENAI_KEY
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temp,
                top_p=top_p,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                max_tokens=max_tokens,
                stop=stop,
                stream=stream
            )
            return response, True

        except Exception as e:
            logger.debug(f"----Completion failed with error:{e}----")
            retry_count += 1
            if retry_count > MAX_RETRY:
                return e, False
            sleep(1)
