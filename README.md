=======
# 🚀 FastAPI Auth Starter

A ready-to-use FastAPI boilerplate with JWT authentication (Access, Refresh, Email verification).

## Features
✅ JWT Access & Refresh Tokens  
✅ Email verification  
✅ Async SQLAlchemy + Alembic  
✅ Modular folder structure  
✅ Background email tasks  

## Tech Stack
- FastAPI
- SQLAlchemy (Async)
- Alembic
- JWT (python-jose)
- Postgres

## Setup
```bash
git clone https://github.com/mahmoudsamy7729/fastapi-starter.git
cd fastapi-starter
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
