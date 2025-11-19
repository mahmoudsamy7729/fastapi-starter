from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # App Info
    app_name: str = "FastAPI Auth System"
    app_env: str = "development"
    app_debug: bool = True
    app_url: str

    # Database
    database_url: str = Field(default=..., alias="DATABASE_URL")
    
    #JWT
    algorithm: str = Field(default=..., alias="ALGORITHM")  
    access_secret_key: str = Field(default=...)
    access_token_expire: int = Field(default=...)
    refresh_secret_key: str = Field(default=...)
    refresh_token_expire: int = Field(default=...)
    validation_secret_key: str = Field(default=...)
    validation_token_expire: int = Field(default=...)



    #MAIL 
    smtp_host: str = Field(default=...)
    smtp_port: int = Field(default=...)
    smtp_user: str = Field(default=...)
    smtp_password: str = Field(default=...)


    #SOCIAL_LOGIN
    google_client_id: str = Field(default=...)
    google_client_secret: str = Field(default=...)
    google_redirect_uri: str = Field(default=...)
    google_auth_url: str = Field(default=...)
    google_token_url: str = Field(default=...)
    google_userinfo_url: str = Field(default=...)


    github_client_id: str = Field(default=...)
    github_client_secret: str = Field(default=...)
    github_redirect_uri: str = Field(default=...)
    github_authorize_url: str = Field(default=...)
    github_token_url: str = Field(default=...)
    github_user_api: str = Field(default=...)
    github_emails: str = Field(default=...)

    

    class Config:
        env_file = BASE_DIR / ".env"


settings = Settings()


