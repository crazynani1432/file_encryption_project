---
title: SecureVault 🔐 Multi-Tier Hybrid Cryptographic File Vault
emoji: 🔐
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Multi-Tier Hybrid Cryptographic File Vault with OTP-Gated Recipient Verification & AES-256-GCM Streaming
---

# SecureVault 🔐 Multi-Tier Hybrid Cryptographic File Vault

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Cryptography](https://img.shields.io/badge/Cryptography-AES--256--GCM-orange.svg)](https://cryptography.io/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20SQLAlchemy-lightgrey.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**SecureVault** is an enterprise-grade, multi-tier hybrid cryptographic file storage and sharing platform. Built on **FastAPI** and modern cryptographic primitives (**AES-256-GCM authenticated encryption** and **PBKDF2-HMAC-SHA256 key derivation**), SecureVault allows senders to seal sensitive data using dynamic access policies—including passphrase challenges, cryptographic security questions, and automated multi-channel One-Time Password (OTP) verification over Email and SMS.

Files are encrypted using a **chunked streaming architecture (64 KB buffers)**, enabling memory-efficient encryption and decryption of large documents without buffering entire payloads in RAM.

---

## 👥 Authors & Contributors

- **Jammula Rithik Reddy** ([@crazynani1432](https://github.com/crazynani1432))
- **Pilli Sai Medhas** ([@pillisaimedhas-dev](https://github.com/pillisaimedhas-dev))
- **Achukatulu Kaif** ([@kaifachukatlu](https://github.com/kaifachukatlu))

---

## 🌟 Key Features

### 🛡️ Multi-Tier Access Policy Engine
Senders can customize granular decryption policies tailored to recipient security clearance:
1. **Tier 1 — Passphrase Challenge (`PASSWORD`)**:
   - The file is encrypted directly with a key derived from a strong passphrase using PBKDF2 with 100,000 iterations and a unique 128-bit salt.
   - Recipient must supply the matching secret passphrase to decrypt and download.
2. **Tier 2 — Cryptographic Security Question (`QUESTION`)**:
   - Ideal for asymmetric knowledge exchange between known parties without external channel access.
   - The challenge answer is normalized and used to derive the decryption key.
3. **Tier 3 — Automated Multi-Channel OTP (`OTP`)**:
   - Zero-knowledge recipient verification.
   - Senders specify the recipient's email address or phone number.
   - The server wraps the ephemeral 256-bit file encryption key using an authenticated 256-bit Server Master Key.
   - Recipients request a time-limited 6-digit OTP dispatched via Gmail SMTP TLS or SMS (Twilio / Fast2SMS).
   - Once validated, an ephemeral, single-use, cryptographically signed JWT download token is minted to authorize streaming decryption.

### 🔒 Cryptographic Rigor & AEAD Security
- **AES-256-GCM (Galois/Counter Mode)**: Guarantees both confidentiality and tamper-proof ciphertext integrity via 128-bit authentication tags.
- **Chunked Streaming (64 KB)**: Encrypts files block-by-block with monotonic chunk counter nonces. Prevents memory exhaustion attacks (DoS) when handling multi-gigabyte files.
- **Master Key Wrapping**: File keys in OTP mode are enveloped using the server master key so raw keys are never stored in plaintext within the database.
- **Constant-Time Hash Comparison**: OTP codes are salted and hashed using SHA-256; verification uses rate-limiting to mitigate brute-force attempts.

### 🎨 Cyberpunk & Glassmorphism UI
- Fully responsive dark-mode dashboard styled with CSS glassmorphism, dynamic glow spheres, and cyberpunk grid styling.
- High-end typography powered by Google Fonts (`Space Grotesk` & `Outfit`).
- Real-time client-side feedback, animated loading spinners, and toast notifications.

---

## 🏗️ Project Architecture

```
file_encryption_project/
├── app/
│   ├── __init__.py                # Application package initialization
│   ├── main.py                    # FastAPI web server, routing & endpoint handlers
│   ├── database.py                # SQLAlchemy ORM session factory & SQLite engine
│   ├── models.py                  # Database schemas (Users, EncryptedFiles, ActiveOTPs)
│   ├── crypto_utils.py            # AES-256-GCM chunked cryptographic engine & PBKDF2
│   ├── otp_service.py             # Multi-channel OTP dispatcher (Console, Gmail SMTP, SMS)
│   ├── static/                    # Frontend assets
│   │   ├── css/
│   │   │   └── style.css          # Glassmorphism cyber-grid aesthetic theme
│   │   └── js/
│   │       └── app.js             # Vault client logic, async uploads & auth handlers
│   └── templates/                 # Jinja2 HTML5 UI templates
│       ├── index.html             # Access authentication & node registration
│       ├── dashboard.html         # User vault, upload manager & file share center
│       └── decrypt.html           # Public recipient verification & decryption portal
├── data/                          # Sample test documents & validation fixtures
│   └── sample.txt                 # Test vector document
├── tests/                         # Automated test suite
│   ├── __init__.py
│   ├── test_crypto.py             # Cryptographic algorithms & key wrapping unit tests
│   └── test_integration.py        # End-to-end integration tests (Auth, Upload, OTP, Download)
├── uploads/                       # Encrypted ciphertext storage directory (.enc blobs)
│   └── .gitkeep
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules (protecting .env, *.db, uploads)
├── LICENSE                        # MIT Open Source License
├── requirements.txt               # Application dependencies
├── run.py                         # Cross-platform Python launcher script
├── start_app.bat                  # 1-click Windows startup batch script
└── README.md                      # Comprehensive project documentation
```

---

## 🔐 Cryptographic Architecture & Flow

```
[ Sender Upload ]
       │
       ▼
Generate Random 128-bit Salt & Ephemeral 256-bit AES Key
       │
       ├─► [PASSWORD / QUESTION Policy]: Derive Key via PBKDF2(passphrase, salt, 100k iters)
       └─► [OTP Policy]: Wrap Key with Server Master Key via AES-256-GCM
       │
       ▼
Stream File in 64 KB Chunks ──► AES-256-GCM Ciphertext ──► Save to disk (uploads/<uuid>.enc)
Save Metadata (File UUID, Policy, Encrypted Key Blob) ──► SQLite Database
       │
       ▼
Generate Unique Shareable Link: http://localhost:8000/share/{file_uuid}

══════════════════════════════════════════════════════════════════════════════════════════════

[ Recipient Download ]
       │
       ▼
Recipient navigates to Share Link
       │
       ├─► [PASSWORD / QUESTION]: Submit answer ──► Verify & Derive File Key
       └─► [OTP]: Click "Send OTP" ──► Dispatched via Email/SMS ──► Submit OTP ──► Unwrap File Key
       │
       ▼
Server generates short-lived, single-use JWT Access Token
       │
       ▼
Browser requests /download?token=... ──► Decrypt 64 KB Chunks in Memory ──► Stream Plaintext to Browser
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+** installed on your system.
- **Git** version control.

### 2. Clone the Repository
```bash
git clone https://github.com/pillisaimedhas-dev/file_encryption_project.git
cd file_encryption_project
```

### 3. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to create your local `.env` file:
```bash
cp .env.example .env
```
Open `.env` and set your preferred keys (e.g., generate a 64-character hex master key):
```ini
# Generate via: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your_generated_jwt_secret_key_here
SERVER_MASTER_KEY=your_64_character_hex_master_key_here

# OTP Provider: console (default for testing), email, or twilio
OTP_PROVIDER=console

# If using Gmail SMTP for real emails:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_gmail_16_character_app_password
```

---

## 💻 Running the Application

### Option A: 1-Click Startup (Windows)
Double-click `start_app.bat` or run:
```powershell
.\start_app.bat
```

### Option B: Python Launcher
```bash
python run.py
```

### Option C: Direct Uvicorn Command
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🌐 Accessing the Platform

- **Web Application Portal:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing Suite

Automated unit tests and end-to-end integration tests are provided in the `tests/` directory:

### Run Cryptographic Unit Tests
Validates key derivation, master key wrapping, 64KB chunked AEAD streaming, and OTP hash generation:
```bash
python tests/test_crypto.py
```

### Run End-to-End Integration Tests
Validates full user registration, login, multi-tier uploads (Password, Security Question, OTP), challenge verification, and streaming download pipelines:
*(Ensure the server is running on port 8000)*
```bash
python tests/test_integration.py
```

---

## 🛡️ Security Design Considerations

- **Zero-Knowledge Decryption**: In `PASSWORD` and `QUESTION` modes, the server never stores or logs the decryption key. If the password is lost, the file cannot be recovered.
- **Tamper Evidence**: Any alteration to ciphertext bits, headers, or salt values causes AES-GCM verification to immediately abort with an `InvalidTag` exception.
- **Short-Lived OTPs & Rate Limiting**: OTPs expire in 5 minutes and are invalidated after 5 failed attempts to prevent automated brute-forcing.
- **Strict Cache Control**: All HTML responses are delivered with `no-cache, no-store, must-revalidate` HTTP headers to prevent sensitive file names and access codes from being cached in public browser history.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
