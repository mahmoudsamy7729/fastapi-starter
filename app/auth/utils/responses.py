from fastapi.responses import JSONResponse


def auth_response(response, access_token: str, refresh_token: str):
    response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,     
            secure=False,   # TRUE for production     
            samesite="lax",    # "none" for production
            max_age=7*24*60*60 
        )

    return JSONResponse(
        content={
        "access_token": access_token,
        "token_type": "bearer"
    }
    )