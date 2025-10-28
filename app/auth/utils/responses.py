from fastapi.responses import JSONResponse


def auth_response(response, access_token: str, refresh_token: str):
    resp = JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"}
    )
    resp.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,       # True in production (HTTPS)
        samesite="lax",     # likely "none" in prod if cross-site
        max_age=7*24*60*60
    )
    return resp