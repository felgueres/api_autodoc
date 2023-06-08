import openai
from time import sleep
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_KEY")
MAX_RETRY = 3
MAX_TOKENS_TO_GENERATE = 80 # Roughly a tweet
ENGINE_1 = 'text-ada-001' 
ENGINE_2 = 'text-davinci-003' 

from logger_config import setup_logger
logger = setup_logger(__name__)

def completion(prompt, engine=ENGINE_2, temp=0.6, top_p=1.0, max_tokens=170, freq_pen=0.25, pres_pen=0.0, stop=['<<END>>']):
    retry_count = 0
    logger.debug(f"Entering completion function with prompt: {prompt}")

    while True: 
        try:
            logger.info(f"Retry count: {retry_count}")
            openai.api_key = OPENAI_KEY 
            response = openai.Completion.create(
                engine=engine,
                prompt=prompt,
                temperature=temp,
                top_p=top_p,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                max_tokens=max_tokens,
                stop=stop
            )
            return response

        except Exception as e:
            logger.debug(f"Completion failed with error: {e}")
            retry_count += 1
            if retry_count > MAX_RETRY:
                logger.info(f"Max retry count exceeded. Returning network error")
                return "Network error"
            sleep(1)