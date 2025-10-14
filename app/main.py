from fastapi import FastAPI
from app.auth.routes import router as auth_router
from app.core.setup_middlewares import setup_middlewares
from app.core.middlewares.rate_limit import limiter
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup logic here")
    yield
    print("Shutdown logic here")

app = FastAPI(lifespan=lifespan)
setup_middlewares(app)


app.include_router(auth_router)
