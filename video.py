from dotenv import load_dotenv
from logger_config import setup_logger
logger = setup_logger(__name__)
from upstream_object import InferenceUtils
from utils import generate_uuid
load_dotenv()
import openai
import os
openai.api_key = os.getenv("OPENAI_KEY")
output_path = "./audio"

MAX_VIDEO_DURATION = 601

def download_audio(video_id, output_path):
    # outputs 
    # dict with title, error

    import yt_dlp 
    ydl_opts = {
        'format': 'bestaudio',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }],
        'outtmpl': output_path 
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_id, download=False)
            duration = info_dict['duration']
            video_title = info_dict['title']
            if duration > MAX_VIDEO_DURATION:
                return {"error": f"The video you selected is too long. Choose videos under 10 minutes."}, False
            else:
                ydl.download(['https://www.youtube.com/watch?v=' + video_id])
                return {'name': video_title}, True 

    except Exception as e:
        print(e)
        return {"error": "Unable to retrieve video."}, False


def transcribe(f):
    transcript = openai.Audio.transcribe("whisper-1", file=f)
    text = transcript['text']
    return text

def process_youtube_video(url):
    source_id = generate_uuid(8)
    base_folder = os.path.dirname(os.path.abspath(__file__))
    yt_video_id = url.split('v=')[1] 
    video_id = yt_video_id.split('&')[0]

    if not os.path.exists(os.path.join(base_folder, "audio")):
        os.makedirs(os.path.join(base_folder, "audio"))

    output_path = os.path.join(base_folder, "audio", source_id)
    fname = output_path + '.mp3'

    try:
        res, success = download_audio(video_id, output_path)
        if not success:
            raise Exception(res['error']) 
        
    except Exception as e:
        return {"error": str(e)}, False
    
    try:
        with open(fname, 'rb') as f:
            text = transcribe(f)
        n_tokens = InferenceUtils.num_tokens_from_string(text)
        res = {"url": url, "n_tokens": n_tokens, "content": text, "link_id": generate_uuid(4), "source_id": generate_uuid(8), "name": res['name']}
        return res, True

    except Exception as e:
        return {"error": str(e)}, False
    
    finally:
        os.remove(fname) if os.path.exists(fname) else None
