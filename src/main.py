import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from slowapi import _rate_limit_exceeded_handler
from src.rate_limiter import limiter
from src.logging import setup_logging
from src.auth.router import router as auth_router


setup_logging()

app = FastAPI()

app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)



@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    method = request.method
    path = request.url.path

    client_host = request.client.host if request.client else "unknown"

    try:
        response = await call_next(request)
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        logger.exception(
            f"{method} {path} from {client_host} -> CRASHED ({duration:.2f}ms): {e}"
        )
        raise

    duration = (time.perf_counter() - start) * 1000
    status = response.status_code

    if status < 400:
        logger.info(f"{method} {path} from {client_host} -> {status} ({duration:.2f}ms)")
    elif status < 500:
        logger.warning(f"{method} {path} from {client_host} -> {status} ({duration:.2f}ms)")
    else:
        logger.error(f"{method} {path} from {client_host} -> {status} ({duration:.2f}ms)")

    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, tags=["auth"])

