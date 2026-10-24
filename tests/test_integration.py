import os
import requests
import sqlite3
import re

BASE_URL = "http://127.0.0.1:8000"

def get_latest_otp_from_db(file_id: str) -> str:
    """Helper to query the SQLite DB directly and recover the 6-digit OTP code."""
    from pathlib import Path
    root_db = Path(__file__).resolve().parent.parent / "secure_vault.db"
    db_path = str(root_db) if root_db.exists() else "./secure_vault.db"
    assert os.path.exists(db_path), f"Database file not found at {db_path}"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query the latest active OTP for this file
    cursor.execute(
        "SELECT otp_code_hash FROM active_otps WHERE file_id = ? ORDER BY created_at DESC LIMIT 1",
        (file_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise ValueError(f"No active OTP found in database for file {file_id}")
        
    target_hash = row[0]
    
    # Recover the 6-digit code by matching the SHA-256 hash
    import hashlib
    for i in range(1000000):
        code = f"{i:06d}"
        if hashlib.sha256(code.encode("utf-8")).hexdigest() == target_hash:
            return code
            
    raise ValueError("Failed to recover OTP from hash")


def run_integration_tests():
    print("Initializing Integration Tests...")
    session = requests.Session()
    
    # 1. Register a test user
    print("Testing Registration...")
    reg_url = f"{BASE_URL}/api/auth/register"
    reg_data = {
        "username": "tester",
        "email": "tester@vault.com",
        "password": "IntegrationPassword1"
    }
    r = session.post(reg_url, data=reg_data)
    # 200 or 400 (if already exists) is fine, let's login
    print("Register Status:", r.status_code)
    
    # 2. Login
    print("Testing Login...")
    login_url = f"{BASE_URL}/api/auth/login"
    login_data = {
        "username_or_email": "tester",
        "password": "IntegrationPassword1"
    }
    r = session.post(login_url, data=login_data)
    assert r.status_code == 200, f"Login failed: {r.text}"
    print("Login successful!")
    
    # Create a test file
    test_content = b"INTEGRATION TEST DATA. SECURE SYMMETRIC STREAM AESGCM VAULT."
    temp_file_path = "temp_integration.txt"
    with open(temp_file_path, "wb") as f:
        f.write(test_content)
        
    try:
        # Tier 1: PASSWORD POLICY TEST
        print("\n--- Tier 1: PASSWORD POLICY TEST ---")
        upload_url = f"{BASE_URL}/api/files/upload"
        with open(temp_file_path, "rb") as f:
            files = {"file": ("temp_integration.txt", f, "text/plain")}
            data = {
                "access_policy": "PASSWORD",
                "password": "SecretPassword99"
            }
            r = session.post(upload_url, files=files, data=data)
        assert r.status_code == 200, f"Upload PASSWORD policy failed: {r.text}"
        file_id = r.json()["file_uuid"]
        print("Uploaded PASSWORD file. ID:", file_id)
        
        # Verify challenge
        verify_url = f"{BASE_URL}/api/files/share/{file_id}/verify-challenge"
        r = requests.post(verify_url, data={"password": "WrongPassword"})
        assert r.status_code == 400, "Challenge should fail with wrong password"
        
        r = requests.post(verify_url, data={"password": "SecretPassword99"})
        assert r.status_code == 200, f"Challenge failed: {r.text}"
        download_token = r.json()["download_token"]
        
        # Stream download
        download_url = f"{BASE_URL}/api/files/share/{file_id}/download"
        r = requests.get(download_url, params={"token": download_token})
        assert r.status_code == 200, f"Stream download failed: {r.text}"
        assert r.content == test_content, "Downloaded plaintext does not match original"
        print("Tier 1 PASSWORD Policy verification PASSED!")
        
        # Tier 2: SECURITY QUESTION POLICY TEST
        print("\n--- Tier 2: SECURITY QUESTION POLICY TEST ---")
        with open(temp_file_path, "rb") as f:
            files = {"file": ("temp_integration.txt", f, "text/plain")}
            data = {
                "access_policy": "QUESTION",
                "security_question": "What is my project code?",
                "security_answer": "Antigravity Project"
            }
            r = session.post(upload_url, files=files, data=data)
        assert r.status_code == 200, f"Upload QUESTION policy failed: {r.text}"
        file_id = r.json()["file_uuid"]
        print("Uploaded QUESTION file. ID:", file_id)
        
        # Verify challenge
        verify_url = f"{BASE_URL}/api/files/share/{file_id}/verify-challenge"
        r = requests.post(verify_url, data={"security_answer": "Wrong Answer"})
        assert r.status_code == 400, "Challenge should fail with wrong answer"
        
        # Verify normalization (spaces and case insensitivity)
        r = requests.post(verify_url, data={"security_answer": "  antigravity  project  "})
        assert r.status_code == 200, f"Challenge failed on normalized answer: {r.text}"
        download_token = r.json()["download_token"]
        
        # Stream download
        download_url = f"{BASE_URL}/api/files/share/{file_id}/download"
        r = requests.get(download_url, params={"token": download_token})
        assert r.status_code == 200, f"Stream download failed: {r.text}"
        assert r.content == test_content, "Downloaded plaintext does not match original"
        print("Tier 2 QUESTION Policy verification PASSED!")
        
        # Tier 3: RECIPIENT OTP POLICY TEST
        print("\n--- Tier 3: RECIPIENT OTP POLICY TEST ---")
        with open(temp_file_path, "rb") as f:
            files = {"file": ("temp_integration.txt", f, "text/plain")}
            data = {
                "access_policy": "OTP",
                "recipient_email": "recipient@vault.com"
            }
            r = session.post(upload_url, files=files, data=data)
        assert r.status_code == 200, f"Upload OTP policy failed: {r.text}"
        file_id = r.json()["file_uuid"]
        print("Uploaded OTP file. ID:", file_id)
        
        # Trigger OTP
        request_otp_url = f"{BASE_URL}/api/files/share/{file_id}/request-otp"
        r = requests.post(request_otp_url, data={"email": "recipient@vault.com"})
        assert r.status_code == 200, f"OTP request failed: {r.text}"
        print("OTP requested successfully!")
        
        # Recover OTP directly from database hash
        otp_code = get_latest_otp_from_db(file_id)
        print("Recovered OTP from database hash:", otp_code)
        
        # Verify challenge
        verify_url = f"{BASE_URL}/api/files/share/{file_id}/verify-challenge"
        r = requests.post(verify_url, data={"otp_code": "000000", "email": "recipient@vault.com"})
        assert r.status_code == 400, "Challenge should fail with wrong OTP"
        
        r = requests.post(verify_url, data={"otp_code": otp_code, "email": "recipient@vault.com"})
        assert r.status_code == 200, f"Challenge failed: {r.text}"
        download_token = r.json()["download_token"]
        
        # Stream download
        download_url = f"{BASE_URL}/api/files/share/{file_id}/download"
        r = requests.get(download_url, params={"token": download_token})
        assert r.status_code == 200, f"Stream download failed: {r.text}"
        assert r.content == test_content, "Downloaded plaintext does not match original"
        print("Tier 3 RECIPIENT OTP Policy verification PASSED!")
        
        print("\nALL MULTI-TIER ACCESS TIERS VERIFIED AND WORKING CORRECTLY!")
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    run_integration_tests()
