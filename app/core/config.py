from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # App Info
    app_name: str = "FastAPI Auth System"
    app_env: str = "development"
    app_debug: bool = True

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    test_database_url: str = Field(..., env="TEST_DATABASE_URL")

    # JWT Config
    secret_key: str = Field(..., env="SECRET_KEY")
    refresh_secret_key: str = Field(..., env="REFRESH_SECRET_KEY")
    verification_secret_key: str = Field(..., env="VERIFICATION_SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_minutes: int = Field(default=10080, env="REFRESH_TOKEN_EXPIRE_MINUTES")
    verification_token_expire_minutes: int = Field(default=15, env="VERIFICATION_TOKEN_EXPIRE_MINUTES")

    #MAIL
    smtp_user: str = Field(..., env="SMTP_USER")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    smtp_host: str = Field(..., env="SMTP_HOST")
    smtp_port: str = Field(..., env="SMTP_PORT")

    #SOCIAL_LOGIN
    google_client_id: str = Field(..., env="GOOGLE_CLINET_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI")


    github_client_id: str = Field(..., env="GITHUB_CLINET_ID")
    github_client_secret: str = Field(..., env="GITHUB_CLIENT_SECRET")
    github_redirect_uri: str = Field(..., env="GITHUB_REDIRECT_URI")


    class Config:
        env_file = ".env"


settings = Settings()
