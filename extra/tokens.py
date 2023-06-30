# TODO: Remove class
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
