from typing import Annotated
from fastapi import Depends
from src.database import db_dependency 
from src.repository import RefreshTokenRepository




def get_refresh_token_repo(db: db_dependency) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)

token_depedency = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repo)]