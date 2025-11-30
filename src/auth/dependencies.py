from typing import Annotated
from fastapi import Depends
from src.auth.repository import UserRepository , LoginCodeRepository, ProfileReposiotry
from src.database import db_dependency
from src.auth_bearer import user_dependency, non_active_user_dependency
from src.auth.emails import Emails


#DATABASE DEBENDCIES 
def get_user_repo(db: db_dependency) -> UserRepository:
    return UserRepository(db)

repo_dependency = Annotated[UserRepository, Depends(get_user_repo)]

def get_code_repo(db: db_dependency) -> LoginCodeRepository:
    return LoginCodeRepository(db)

code_dependency = Annotated[LoginCodeRepository, Depends(get_code_repo)]

def get_profile_repo(db: db_dependency) -> ProfileReposiotry:
    return ProfileReposiotry(db)

profile_dependency = Annotated[ProfileReposiotry, Depends(get_profile_repo)]


async def get_email_service():
    return Emails()

email_dependency = Annotated[Emails, Depends(get_email_service)]