from fastapi import HTTPException, status

class TokenExcpetions:
    @staticmethod
    def token_excep(status , detail):
        return HTTPException(
        status_code= status,
        detail= detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

