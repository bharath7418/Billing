
import os, json
from dotenv import load_dotenv

load_dotenv()

class Config() :
    SECRET_KEY = os.getenv('SECRET_KEY')

    raw_db_url = os.getenv('DATABASE_URL')
    use_tmp_sqlite = os.getenv('VERCEL') == '1'
    if raw_db_url:
        SQLALCHEMY_DATABASE_URI = raw_db_url.replace("postgres://", "postgresql://", 1)
    elif use_tmp_sqlite:
        SQLALCHEMY_DATABASE_URI =  'sqlite:////tmp/database.db'
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
