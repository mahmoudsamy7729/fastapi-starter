from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import status, Request


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = {
        err["loc"][-1]: err["msg"]
        for err in exc.errors()
    }
    
    return JSONResponse(
        status_code=422,
        content={"errors": errors},
    )