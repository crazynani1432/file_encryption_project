import os
import uuid
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Form, UploadFile, File, Response, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

try:
    from app import models
    from app import crypto_utils
    from app import otp_service
    from app.database import engine, get_db
except (ImportError, ValueError):
    import models
    import crypto_utils
    import otp_service
    from database import engine, get_db

# Initialize Database tables
models.Base.metadata.create_all(bind=engine)

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Load configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key_change_me_in_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(PROJECT_ROOT, "uploads"))

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Secure Multi-Tier File Vault")

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if "text/html" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Templates and Static configuration
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount static directory
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# JWT helper functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def get_current_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
        return db.query(models.User).filter(models.User.id == user_id).first()
    except jwt.PyJWTError:
        return None


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_current_user_from_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or user not found",
        )
    return user


# Page Rendering Routes

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token")
    if token:
        user = get_current_user_from_token(token, db)
        if user:
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token")
    if not token:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    user = get_current_user_from_token(token, db)
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user})


@app.get("/share/{file_id}", response_class=HTMLResponse)
async def read_share(request: Request, file_id: str, db: Session = Depends(get_db)):
    file_record = db.query(models.EncryptedFile).filter(models.EncryptedFile.id == file_id).first()
    if not file_record:
        return templates.TemplateResponse(request=request, name="decrypt.html", context={"error": "File not found", "file": None})
    return templates.TemplateResponse(request=request, name="decrypt.html", context={
        "file": file_record,
        "error": None
    })


# API Authentication Endpoints

@app.post("/api/auth/register")
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate fields
    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="All fields are required")
        
    db_user = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    # Hash password using bcrypt
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    # Create new user
    new_user = models.User(
        username=username,
        email=email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Registration successful"}


@app.post("/api/auth/login")
async def login(
    username_or_email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Lookup by username or email
    user = db.query(models.User).filter(
        (models.User.username == username_or_email) | (models.User.email == username_or_email)
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Verify password
    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Generate session token
    access_token = create_access_token(data={"user_id": user.id})
    
    response = JSONResponse(content={"message": "Login successful", "username": user.username})
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        max_age=3600
    )
    return response


@app.post("/api/auth/logout")
async def logout(response: Response):
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("session_token")
    return response


@app.get("/api/auth/me")
async def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone_number": current_user.phone_number
    }


# API File Cryptography and Access Management

@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    access_policy: str = Form(...),
    password: Optional[str] = Form(None),
    security_question: Optional[str] = Form(None),
    security_answer: Optional[str] = Form(None),
    recipient_email: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Basic parameter validation
    if access_policy not in ("PASSWORD", "QUESTION", "OTP"):
        raise HTTPException(status_code=400, detail="Invalid access policy type")

    # Key derivation & parameters configuration
    salt = os.urandom(16)
    file_key = None
    wrapped_key = None

    if access_policy == "PASSWORD":
        if not password or len(password) < 4:
            raise HTTPException(status_code=400, detail="Password of at least 4 characters is required")
        file_key = crypto_utils.derive_key_from_password(password, salt)

    elif access_policy == "QUESTION":
        if not security_question or not security_answer:
            raise HTTPException(status_code=400, detail="Security question and answer are required")
        # Normalize the answer
        normalized_answer = security_answer.strip().lower().replace(" ", "")
        if len(normalized_answer) == 0:
            raise HTTPException(status_code=400, detail="Invalid security question answer")
        file_key = crypto_utils.derive_key_from_password(normalized_answer, salt)

    elif access_policy == "OTP":
        if not recipient_email:
            raise HTTPException(status_code=400, detail="Valid recipient email address is required")
        emails = [e.strip() for e in recipient_email.split(",") if e.strip()]
        if not emails:
            raise HTTPException(status_code=400, detail="Valid recipient email address is required")
        for email_addr in emails:
            if "@" not in email_addr:
                raise HTTPException(status_code=400, detail=f"Invalid recipient email address: {email_addr}")
        # Generate random file encryption key
        file_key = os.urandom(32)
        # Wrap it with server master key
        wrapped_key = crypto_utils.encrypt_key_with_master(file_key)

    # Prepare safe local storage path
    file_uuid = str(uuid.uuid4())
    stored_filename = f"{file_uuid}.enc"
    stored_filepath = os.path.join(UPLOAD_DIR, stored_filename)

    # Perform chunked file encryption & write to storage
    try:
        with open(stored_filepath, "wb") as out_f:
            crypto_utils.encrypt_file(file.file, out_f, file_key, salt)
    except Exception as e:
        # Cleanup file if writing failed
        if os.path.exists(stored_filepath):
            os.remove(stored_filepath)
        raise HTTPException(status_code=500, detail=f"Failed to encrypt and store file: {str(e)}")

    # Store entry in database
    encrypted_file = models.EncryptedFile(
        id=file_uuid,
        filename=file.filename,
        filepath=stored_filepath,
        access_policy=access_policy,
        sender_id=current_user.id,
        recipient_email=recipient_email.strip() if recipient_email else None,
        security_question=security_question.strip() if security_question else None,
        encrypted_file_key=wrapped_key
    )
    db.add(encrypted_file)
    db.commit()
    db.refresh(encrypted_file)

    share_url = f"/share/{file_uuid}"
    return {
        "message": "File encrypted and stored successfully",
        "file_uuid": file_uuid,
        "filename": file.filename,
        "share_url": share_url
    }


@app.get("/api/files/my-files")
async def get_my_files(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    files = db.query(models.EncryptedFile).filter(
        models.EncryptedFile.sender_id == current_user.id
    ).order_by(models.EncryptedFile.created_at.desc()).all()
    
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "access_policy": f.access_policy,
            "recipient_email": f.recipient_email,
            "security_question": f.security_question,
            "download_count": f.download_count,
            "created_at": f.created_at.isoformat() + "Z"
        }
        for f in files
    ]


@app.delete("/api/files/delete/{file_id}")
async def delete_file(
    file_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record = db.query(models.EncryptedFile).filter(
        models.EncryptedFile.id == file_id,
        models.EncryptedFile.sender_id == current_user.id
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found or unauthorized")

    # Delete ciphertext from disk
    if os.path.exists(file_record.filepath):
        try:
            os.remove(file_record.filepath)
        except Exception as e:
            print(f"[Backend Error] Failed to delete file from disk: {e}")

    # Delete database record
    db.delete(file_record)
    db.commit()

    return {"message": "File deleted successfully"}


@app.post("/api/files/send-link/{file_id}")
async def send_file_link_via_gmail(
    file_id: str,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sends the file's share link to all authorized recipient email addresses
    via the configured sender email account.
    Only works for OTP-policy files owned by the authenticated user.
    """
    file_record = db.query(models.EncryptedFile).filter(
        models.EncryptedFile.id == file_id,
        models.EncryptedFile.sender_id == current_user.id
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found or unauthorized")

    if file_record.access_policy != "OTP":
        raise HTTPException(status_code=400, detail="Share link email is only available for OTP-policy files")

    if not file_record.recipient_email:
        raise HTTPException(status_code=400, detail="No recipient email address configured for this file")

    # Build the absolute share URL
    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/share/{file_id}"

    # Send to each recipient with their email pre-filled in the URL
    recipients = [e.strip() for e in file_record.recipient_email.split(",") if e.strip()]
    failed = []
    for recipient in recipients:
        import urllib.parse
        recipient_share_url = f"{share_url}?email={urllib.parse.quote(recipient)}"
        success = otp_service.send_file_share_link(
            recipient=recipient,
            filename=file_record.filename,
            sender_name=current_user.username,
            share_url=recipient_share_url
        )
        if not success:
            failed.append(recipient)

    if failed:
        raise HTTPException(
            status_code=500,
            detail=f"Email dispatch failed for: {', '.join(failed)}"
        )

    count = len(recipients)
    return {
        "message": f"Share link sent to {count} recipient{'s' if count > 1 else ''} via Gmail successfully."
    }

# Recipient Portal API Access & Verification Endpoints

@app.get("/api/files/share/{file_id}/meta")
async def get_share_meta(file_id: str, db: Session = Depends(get_db)):
    file_record = db.query(models.EncryptedFile).filter(models.EncryptedFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Share link not found")
        
    return {
        "id": file_record.id,
        "filename": file_record.filename,
        "access_policy": file_record.access_policy,
        "security_question": file_record.security_question,
        "sender": file_record.sender.username
    }


@app.post("/api/files/share/{file_id}/request-otp")
async def request_otp_for_file(
    file_id: str,
    email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    file_record = db.query(models.EncryptedFile).filter(models.EncryptedFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    if file_record.access_policy != "OTP":
        raise HTTPException(status_code=400, detail="This file is not configured for OTP verification")

    if not email:
        raise HTTPException(status_code=400, detail="Recipient email address is required to request OTP")
        
    target_email = email.strip().lower()
    auth_emails = [e.strip().lower() for e in file_record.recipient_email.split(",") if e.strip()]
    if target_email not in auth_emails:
        raise HTTPException(status_code=400, detail="This email address is not authorized to access this file.")

    # Check for cooldown: prevent spamming OTP requests (limit to once every 30 seconds per email)
    recent_otp = db.query(models.ActiveOTP).filter(
        models.ActiveOTP.file_id == file_id,
        models.ActiveOTP.email == target_email,
        models.ActiveOTP.created_at > datetime.now(timezone.utc) - timedelta(seconds=30)
    ).first()
    if recent_otp:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="An OTP was sent recently to this email. Please wait 30 seconds."
        )

    # Generate and hash verification OTP
    otp_code = otp_service.generate_otp()
    hashed_code = otp_service.hash_otp(otp_code)

    # Create DB verification record
    new_otp = models.ActiveOTP(
        file_id=file_record.id,
        email=target_email,
        otp_code_hash=hashed_code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    db.add(new_otp)
    db.commit()

    # Dispatch SMS or Email
    provider = otp_service.get_otp_provider(target_email)
    success = provider.send_otp(target_email, otp_code)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to dispatch verification OTP. Contact system administrator.")

    return {"message": "Verification code dispatched successfully"}


@app.post("/api/files/share/{file_id}/verify-challenge")
async def verify_challenge_meta(
    file_id: str,
    password: Optional[str] = Form(None),
    security_answer: Optional[str] = Form(None),
    otp_code: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Validates challenge parameters and returns temporary validation details or stream tokens.
    For ease of streaming downloads directly in HTML, we will verify credentials and then initiate
    the Stream response directly if valid. This POST route can verify credentials first to return clean JSON errors
    if they are incorrect. If they are correct, it returns a 200 validation success, and the frontend
    subsequently initiates the download using an standard GET request with the verified challenge parameters.
    """
    file_record = db.query(models.EncryptedFile).filter(models.EncryptedFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    derived_key = None

    if file_record.access_policy == "PASSWORD":
        if not password:
            raise HTTPException(status_code=400, detail="Password parameter is missing")
        # Load salt from file header
        if not os.path.exists(file_record.filepath):
            raise HTTPException(status_code=404, detail="Encrypted file not found on disk")
        with open(file_record.filepath, "rb") as f:
            salt = f.read(16)
        derived_key = crypto_utils.derive_key_from_password(password, salt)

    elif file_record.access_policy == "QUESTION":
        if not security_answer:
            raise HTTPException(status_code=400, detail="Security answer parameter is missing")
        # Load salt
        if not os.path.exists(file_record.filepath):
            raise HTTPException(status_code=404, detail="Encrypted file not found on disk")
        with open(file_record.filepath, "rb") as f:
            salt = f.read(16)
        normalized = security_answer.strip().lower().replace(" ", "")
        derived_key = crypto_utils.derive_key_from_password(normalized, salt)

    elif file_record.access_policy == "OTP":
        if not otp_code:
            raise HTTPException(status_code=400, detail="OTP code parameter is missing")
        if not email:
            raise HTTPException(status_code=400, detail="Email parameter is missing")
        
        target_email = email.strip().lower()
        # Retrieve the latest active OTP
        active_otp = db.query(models.ActiveOTP).filter(
            models.ActiveOTP.file_id == file_id,
            models.ActiveOTP.email == target_email,
            models.ActiveOTP.verified == False,
            models.ActiveOTP.expires_at > datetime.now(timezone.utc)
        ).order_by(models.ActiveOTP.created_at.desc()).first()

        if not active_otp:
            raise HTTPException(status_code=400, detail="No active or valid verification OTP found. Request a new OTP.")

        if active_otp.attempts >= 3:
            raise HTTPException(status_code=400, detail="OTP expired due to too many failed attempts. Request a new OTP.")

        hashed_input = otp_service.hash_otp(otp_code)
        if active_otp.otp_code_hash != hashed_input:
            active_otp.attempts += 1
            db.commit()
            remaining = 3 - active_otp.attempts
            raise HTTPException(status_code=400, detail=f"Invalid OTP code. Retries remaining: {remaining}")

        # Mark OTP as verified so it can't be reused
        active_otp.verified = True
        db.commit()
        
        # In OTP mode, key is decrypted from file record key using server master key
        try:
            derived_key = crypto_utils.decrypt_key_with_master(file_record.encrypted_file_key)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to decrypt the file key using Master Key")

    # Verify key authenticity by testing decryption of the first chunk
    try:
        test_generator = crypto_utils.decrypt_file_generator(file_record.filepath, derived_key)
        next(test_generator)
    except StopIteration:
        # File is empty, key is correct
        pass
    except Exception:
        raise HTTPException(status_code=400, detail="Access challenge verification failed. Key is incorrect.")

    # Create a temporary single-use download token to authorize the streaming GET request
    token_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
    # Store the derived key (hex encoded) temporarily inside a secure short-lived token
    token_payload = {
        "file_id": file_id,
        "key_hex": derived_key.hex(),
        "exp": token_expiry
    }
    download_token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return {"message": "Challenge verified", "download_token": download_token}


@app.get("/api/files/share/{file_id}/download")
async def download_file_stream(
    file_id: str,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Receives a valid, short-lived download token, verifies it, retrieves the file,
    and streams decrypted chunks directly back to the recipient browser.
    """
    # Verify the download token
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("file_id") != file_id:
            raise HTTPException(status_code=400, detail="Invalid token target file")
        key_hex = payload.get("key_hex")
        if not key_hex:
            raise HTTPException(status_code=400, detail="Key missing in token")
        key = bytes.fromhex(key_hex)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Download link expired. Please verify access again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid access token")

    file_record = db.query(models.EncryptedFile).filter(models.EncryptedFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File metadata not found")

    if not os.path.exists(file_record.filepath):
        raise HTTPException(status_code=404, detail="Physical file not found on disk")

    # Increment download count
    file_record.download_count += 1
    db.commit()

    # Generate custom filename
    safe_filename = file_record.filename.replace('"', '\\"')

    # Stream the decryption directly
    return StreamingResponse(
        crypto_utils.decrypt_file_generator(file_record.filepath, key),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Cache-Control": "no-cache"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

