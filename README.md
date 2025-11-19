# FastAPI Authentication System  
### JWT Access/Refresh Tokens • Rotation • OAuth (Google & GitHub) • OTP Login • Email Verification

A high-security authentication system built with **FastAPI**, featuring:

- 🔐 JWT Access/Refresh Tokens  
- 🔁 **Secure Refresh Token Rotation (DB-backed)**  
- 📧 Email Verification & Password Reset  
- 🔑 Google OAuth2 & GitHub OAuth2  
- 🔢 One-Time Password (OTP) Login  
- 🧵 Async Architecture + CPU-bound hashing in ThreadPool  
- 🗃️ Repository Pattern + Service Layer  
- ⚙️ Environment-based configuration  
- 📦 Fully modular & production-ready structure  

---

## 🚀 Features

### 🔐 **JWT Authentication**
- Access Token (short-lived)
- Refresh Token (long-lived)
- Rotation logic (old token revoked → new token issued)
- Refresh tokens stored securely in DB (hashed)
- All tokens include `jti` for tracking

### 🔁 **Refresh Token Rotation**
- Detect invalid/expired/unknown refresh tokens
- Revoke old token after issuing new one
- Delete all previous tokens on login (single-session mode)

### 🔑 **OAuth 2.0**
- Google Login
- GitHub Login
- Secure `state` verification
- Cookie-based refresh token storage

### 🔢 **OTP Login**
- Generate 6-digit OTP
- Store hashed OTP in database
- Auto-expiration
- Login with email + OTP

### 📧 **Email Flows**
- Email verification
- Password reset
- Welcome email
- SMTP via FastMail

### 🧵 **Async Backend**
- Async SQLAlchemy (asyncpg)
- Async HTTPX for OAuth
- run_in_threadpool for heavy hashing

---

## 🛠️ Tech Stack

### **Backend**
- FastAPI 
- Python 3.12+
- SQLAlchemy 2.0 (async) 
- asyncpg (PostgreSQL driver)
- Pydantic v2
- Passlib + Argon2 for password hashing 
- HTTPX (async OAuth & API calls) 
- FastAPI-Mail (SMTP integration)

### **Auth**
- python-jose (JWT) 
- Google OAuth
- GitHub OAuth

### **Utilities**
- python-dotenv 
- Alembic (database migrations) 
- Uvicorn (server)

---

## 🏃 Running the Project

### 1. Install dependencies
```bash
pip install -r requirements/development.txt
alembic upgrade head
uvicorn src.main:app --reload

```

---

## 🔁 Refresh Token Rotation (Flow)

1. User logs in → access & refresh token are generated  
2. Refresh token is stored **hashed** in the database  
3. User requests `/refresh/token`  
4. Backend verifies the JWT signature  
5. Extracts the `jti` from the refresh token  
6. Fetches the token row from the database  
7. Validates that the token:  
   - exists  
   - is not revoked  
   - is not expired  
8. Issues a new access token + new refresh token  
9. Revokes the old refresh token (rotation)  
10. Stores the new refresh token in the database  
11. Returns new access token + sets new refresh cookie

---

## 🔑 OAuth Flow (Google / GitHub)

1. Redirect user to provider login page  
2. User authorizes the application  
3. Provider sends back a `code` + `state`  
4. Backend validates the `state` (CSRF protection)  
5. Exchanges the `code` for an access token  
6. Uses provider access token to fetch user profile  
7. Creates the user in DB if not existing  
8. Generates JWT access & refresh tokens  
9. Stores refresh token in DB  
10. Sets refresh cookie + returns access token

---

## 📧 OTP Login Flow

1. User enters email  
2. Backend generates a 6-digit OTP  
3. OTP is hashed and stored in the database  
4. OTP is emailed to the user  
5. User submits the OTP  
6. Backend verifies the hashed OTP  
7. If valid → generate access & refresh tokens  
8. Delete OTP after successful login  
9. Set refresh cookie + return access token


---

## 📜 License

This project is licensed under the **MIT License** — free for personal and commercial use.





