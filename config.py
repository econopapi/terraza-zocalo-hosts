import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Tu connection string de Supabase
    # Formato: postgresql://postgres:[PASSWORD]@[HOST]/postgres
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'tu-secret-key-super-segura')
    TIMEZONE = 'America/Mexico_City'