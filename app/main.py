from fastapi import FastAPI
from app.auth.routes.auth import router as auth_router
from app.auth.routes.social import router as social_router
from app.users.routes.users import router as users_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.setup_middlewares import setup_middlewares
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup logic here")
    yield
    print("Shutdown logic here")

app = FastAPI(lifespan=lifespan)
#setup_middlewares(app)

origins = [
    "http://localhost:3000",  # if you have a React/Vue frontend
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],  # or ["POST", "OPTIONS"]
    allow_headers=["*"],  # or ["Content-Type", "Authorization"]
)

app.include_router(auth_router)
app.include_router(social_router)
app.include_router(users_router)
