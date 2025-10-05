from pydantic import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DATABASE_URL: str = "postgresql://quark_user:quark_password@localhost:5432/quark_db"
    SECRET_KEY: str = "a-very-secret-key-that-should-be-in-a-env-file"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()