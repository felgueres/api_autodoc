SQLITE_DB = 'sqlite.db'
DATA_SOURCES_TABLE = 'data_sources'
DTYPE_PDF = 'pdf'
DTYPE_TXT = 'txt'
DTYPE_CSV = 'csv'
DTYPE_URL = 'url'
DTYPE_PNG = 'png'
DTYPE_VIDEO = 'video'
MAX_FILE_SIZE = 16 * 1024 * 1024
EMPTY_STRING = ''
USERS_WITH_GPT4=['@gmail.com']
DEMO_USER = 'hi@upstreamapi.com'

MIMETYPES = {
    'pdf': 'application/pdf',
    'txt': 'text/plain',
    'csv': 'text/csv',
    'url': 'text/plain',
    'png': 'image/png',
    'video': 'video/mp4'
}

PLANS = {
  'free': {
    'name': 'FREE',
    'maxMessages': 30,
    'maxBots': 5,
    'desc': 'Easiest way to try Upstream',
    'button': False
  },
  'pro': {
    'name': 'Upstream Basic',
    'price': '10USD/mo',
    'maxMessages': 2000,
    'maxBots': 10,
    'desc': 'Best for occasional users',
    'button': True,
  },
  'business': {
    'name': 'Upstream Pro',
    'price': '24USD/mo',
    'maxMessages': 10000,
    'maxBots': 30,
    'desc': 'Best for power users',
    'button': True,
  },
}
