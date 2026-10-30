import os
import random
import hashlib
import urllib.request
import urllib.parse
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
_env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()


class OTPProvider:
    def send_otp(self, recipient: str, otp_code: str, filename: Optional[str] = None) -> bool:
        raise NotImplementedError

    def send_share_link(self, recipient: str, filename: str, sender_name: str, share_url: str, reply_to: Optional[str] = None) -> bool:
        raise NotImplementedError


class ConsoleOTPProvider(OTPProvider):
    def send_otp(self, recipient: str, otp_code: str, filename: Optional[str] = None) -> bool:
        file_info = f" for file: {filename}" if filename else ""
        print("\n" + "=" * 60)
        print(f" [SECURE VAULT] MOCK OTP DISPATCH{file_info}")
        print(f" Recipient: {recipient}")
        print(f" Active OTP Code: {otp_code}")
        print(f" Expiry duration: 5 minutes")
        print("=" * 60 + "\n")
        return True

    def send_share_link(self, recipient: str, filename: str, sender_name: str, share_url: str, reply_to: Optional[str] = None) -> bool:
        print("\n" + "=" * 60)
        print(f" [SECURE VAULT] MOCK FILE SHARE LINK DISPATCH")
        print(f" Recipient: {recipient}")
        print(f" Shared by: {sender_name}")
        print(f" File: {filename}")
        print(f" Share URL: {share_url}")
        print("=" * 60 + "\n")
        return True


class TwilioOTPProvider(OTPProvider):
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER")

    def send_otp(self, recipient: str, otp_code: str, filename: Optional[str] = None) -> bool:
        if not self.account_sid or not self.auth_token or not self.from_phone:
            print("[OTP Service ERROR] Twilio configuration is missing. Falling back to Console logging.")
            return ConsoleOTPProvider().send_otp(recipient, otp_code, filename)

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        file_text = f" for '{filename}'" if filename else ""
        data = urllib.parse.urlencode({
            "To": recipient,
            "From": self.from_phone,
            "Body": f"Your Secure Vault verification code{file_text} is: {otp_code}. It is valid for 5 minutes."
        }).encode("utf-8")

        import base64
        auth_str = f"{self.account_sid}:{self.auth_token}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {auth_b64}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode("utf-8")
                res_data = json.loads(res_body)
                print(f"[OTP Service] Twilio message sent successfully. SID: {res_data.get('sid')}")
                return True
        except Exception as e:
            print(f"[OTP Service ERROR] Twilio request failed: {e}")
            return False

    def send_share_link(self, recipient: str, filename: str, sender_name: str, share_url: str, reply_to: Optional[str] = None) -> bool:
        if not self.account_sid or not self.auth_token or not self.from_phone:
            return ConsoleOTPProvider().send_share_link(recipient, filename, sender_name, share_url)
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = urllib.parse.urlencode({
            "To": recipient,
            "From": self.from_phone,
            "Body": f"Secure Vault: {sender_name} shared '{filename}' with you. Access link: {share_url}"
        }).encode("utf-8")
        import base64
        auth_str = f"{self.account_sid}:{self.auth_token}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {auth_b64}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req) as response:
                return True
        except Exception as e:
            print(f"[OTP Service ERROR] Twilio share link dispatch failed: {e}")
            return False


class Fast2SMSOTPProvider(OTPProvider):
    def __init__(self):
        self.api_key = os.getenv("FAST2SMS_API_KEY")

    def send_otp(self, recipient: str, otp_code: str, filename: Optional[str] = None) -> bool:
        if not self.api_key:
            print("[OTP Service ERROR] Fast2SMS API key is missing. Falling back to Console logging.")
            return ConsoleOTPProvider().send_otp(recipient, otp_code, filename)

        url = "https://www.fast2sms.com/dev/bulkV2"
        cleaned_phone = "".join(filter(str.isdigit, recipient))
        if len(cleaned_phone) == 12 and cleaned_phone.startswith("91"):
            cleaned_phone = cleaned_phone[2:]

        params = {
            "route": "q",
            "message": f"Your Secure Vault OTP is {otp_code}. Valid for 5 minutes.",
            "language": "english",
            "flash": 0,
            "numbers": cleaned_phone
        }

        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"

        req = urllib.request.Request(full_url, method="GET")
        req.add_header("authorization", self.api_key)
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode("utf-8")
                res_data = json.loads(res_body)
                if res_data.get("return") is True:
                    print(f"[OTP Service] Fast2SMS sent successfully: {res_data.get('message')}")
                    return True
                else:
                    print(f"[OTP Service ERROR] Fast2SMS API returned failure: {res_data}")
                    return False
        except Exception as e:
            print(f"[OTP Service ERROR] Fast2SMS request failed: {e}")
            return False

    def send_share_link(self, recipient: str, filename: str, sender_name: str, share_url: str, reply_to: Optional[str] = None) -> bool:
        return ConsoleOTPProvider().send_share_link(recipient, filename, sender_name, share_url, reply_to=reply_to)


class EmailOTPProvider(OTPProvider):
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "587").strip())
        self.sender_email = (os.getenv("SENDER_EMAIL") or "").strip()
        # Clean any whitespace or spaces commonly present in 16-character Google App Passwords
        raw_password = os.getenv("SENDER_PASSWORD") or ""
        self.sender_password = raw_password.replace(" ", "").strip()

    def _send_smtp_email(
        self,
        recipient: str,
        subject: str,
        text_content: str,
        html_content: str,
        reply_to: Optional[str] = None
    ) -> bool:
        if not self.sender_email or not self.sender_password:
            print("[Email Service ERROR] SMTP credentials missing in .env (SENDER_EMAIL or SENDER_PASSWORD). Falling back to Console logging.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = f"Secure Vault <{self.sender_email}>"
        msg["To"] = recipient
        if reply_to:
            msg["Reply-To"] = reply_to

        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")

        msg.attach(part1)
        msg.attach(part2)

        server = None
        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=25)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=25)
                server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
        except Exception as e:
            print(f"[Email Service ERROR] Email dispatch failed to {recipient}: {e}")
            return False
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

        try:
            print(f"[Email Service] Email successfully sent to {recipient}")
        except Exception:
            pass
        return True

    def send_share_link(self, recipient: str, filename: str, sender_name: str, share_url: str, reply_to: Optional[str] = None) -> bool:
        """
        Send access link to the recipient when an encrypted file is uploaded.
        """
        subject = f"🔐 Secure Vault: '{filename}' has been securely shared with you"
        
        text_content = (
            f"Hello,\n\n"
            f"{sender_name} has shared a securely encrypted file with you on Secure Vault.\n\n"
            f"File: {filename}\n"
            f"Access Link: {share_url}\n\n"
            f"How to access:\n"
            f"1. Click or copy the access link above into your browser.\n"
            f"2. On the secure page, request your 6-digit One-Time Verification Passcode (OTP).\n"
            f"3. A separate email with your OTP code will be sent to this email address to verify your identity and decrypt the file.\n\n"
            f"Secure Vault Systems • Hybrid Cryptographic Protection\n"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #c9d1d9; margin: 0; padding: 24px;">
  <div style="max-width: 580px; margin: 0 auto; background: #131b2e; border: 1px solid #1f2d4d; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 24px; text-align: center; border-bottom: 1px solid #1e293b;">
      <div style="font-size: 26px; font-weight: 800; color: #60a5fa; letter-spacing: 2px;">🔒 SECURE<span style="color:#ffffff;">VAULT</span></div>
      <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Zero-Knowledge Cryptographic Transfer</div>
    </div>
    <div style="padding: 30px 24px; color: #e2e8f0;">
      <h2 style="margin-top: 0; color: #ffffff; font-size: 20px;">Encrypted File Shared With You</h2>
      <p style="font-size: 15px; line-height: 1.6; color: #cbd5e1;">
        <strong style="color: #60a5fa;">{sender_name}</strong> has shared an end-to-end encrypted file with you on <strong>Secure Vault</strong>.
      </p>
      
      <div style="background: #090d16; border: 1px solid #2563eb44; border-radius: 10px; padding: 18px; margin: 24px 0;">
        <div style="font-size: 12px; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; margin-bottom: 6px;">Protected File Name</div>
        <div style="font-size: 17px; font-weight: bold; color: #60a5fa; word-break: break-all;">📄 {filename}</div>
        <div style="margin-top: 12px; font-size: 12px; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; margin-bottom: 4px;">Security Tier</div>
        <div style="font-size: 14px; color: #34d399; font-weight: 600;">✉️ Dynamic Email OTP Authentication</div>
      </div>

      <div style="text-align: center; margin: 30px 0;">
        <a href="{share_url}" style="display: inline-block; background: linear-gradient(135deg, #3b82f6, #2563eb); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 14px rgba(37,99,235,0.4);">Access & Decrypt File</a>
      </div>

      <div style="background: rgba(30, 41, 59, 0.5); border-left: 4px solid #3b82f6; padding: 14px; border-radius: 6px; margin-top: 20px;">
        <div style="font-weight: 600; font-size: 14px; color: #f8fafc; margin-bottom: 4px;">🔐 How It Works:</div>
        <div style="font-size: 13px; line-height: 1.5; color: #94a3b8;">
          1. Click the button above to open the secure vault download portal.<br>
          2. Click <strong>"Request Verification OTP"</strong> on the page.<br>
          3. A <strong>separate email</strong> containing your 6-digit verification code will be sent immediately to verify your identity and decrypt the file.
        </div>
      </div>

      <p style="font-size: 12px; color: #64748b; margin-top: 24px; word-break: break-all;">
        Direct link: <a href="{share_url}" style="color: #60a5fa;">{share_url}</a>
      </p>
    </div>
    <div style="padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #1e293b; background: #0c111d;">
      Secured with Hybrid Encryption • Zero Local Data Footprint<br>
      © Secure Vault Systems
    </div>
  </div>
</body>
</html>"""

        success = self._send_smtp_email(recipient, subject, text_content, html_content, reply_to=reply_to)
        if not success:
            ConsoleOTPProvider().send_share_link(recipient, filename, sender_name, share_url, reply_to=reply_to)
            return False
        return True

    def send_otp(self, recipient: str, otp_code: str, filename: Optional[str] = None) -> bool:
        """
        Send verification OTP in a separate email to the target address.
        """
        file_desc = f" for '{filename}'" if filename else ""
        subject = f"🔑 Your Secure Vault Verification Code: {otp_code}"

        text_content = (
            f"Your Secure Vault verification code{file_desc} is: {otp_code}\n\n"
            "This code is time-sensitive and is valid for 5 minutes.\n"
            "Enter this 6-digit code on the file download page to decrypt and stream your file.\n\n"
            "If you did not request this verification code, please ignore this email.\n\n"
            "Secure Vault Systems\n"
        )

        target_file_html = (
            f'<div style="background:#090d16; border:1px solid #1f2d4d; border-radius:8px; padding:12px; margin-bottom:18px; font-size:14px; color:#94a3b8;">'
            f'Target File: <strong style="color:#60a5fa;">{filename}</strong></div>'
            if filename else ''
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #c9d1d9; margin: 0; padding: 24px;">
  <div style="max-width: 580px; margin: 0 auto; background: #131b2e; border: 1px solid #1f2d4d; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 24px; text-align: center; border-bottom: 1px solid #1e293b;">
      <div style="font-size: 26px; font-weight: 800; color: #60a5fa; letter-spacing: 2px;">🔒 SECURE<span style="color:#ffffff;">VAULT</span></div>
      <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Identity Verification Required</div>
    </div>
    <div style="padding: 30px 24px; color: #e2e8f0; text-align: center;">
      <h2 style="margin-top: 0; color: #ffffff; font-size: 20px;">Your One-Time Passcode (OTP)</h2>
      <p style="font-size: 15px; color: #94a3b8; margin-bottom: 20px;">
        Use the 6-digit code below to verify your identity and decrypt your file.
      </p>

      {target_file_html}

      <div style="background: #090d16; border: 2px dashed #3b82f6; border-radius: 12px; padding: 20px; margin: 24px auto; max-width: 320px;">
        <div style="font-size: 38px; font-weight: 800; letter-spacing: 8px; color: #34d399; font-family: monospace;">{otp_code}</div>
        <div style="font-size: 13px; color: #94a3b8; margin-top: 8px;">⏱️ Valid for 5 minutes</div>
      </div>

      <p style="font-size: 14px; color: #cbd5e1; line-height: 1.5; margin-top: 20px;">
        Enter this code in the Secure Vault access portal to decrypt and download your file stream directly.
      </p>

      <p style="font-size: 12px; color: #64748b; margin-top: 24px;">
        If you did not request this verification code, you can safely ignore this email.
      </p>
    </div>
    <div style="padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #1e293b; background: #0c111d;">
      Zero Knowledge Security • Hybrid Decryption<br>
      © Secure Vault Systems
    </div>
  </div>
</body>
</html>"""

        success = self._send_smtp_email(recipient, subject, text_content, html_content)
        if not success:
            ConsoleOTPProvider().send_otp(recipient, otp_code, filename)
            return False
        return True


def get_otp_provider(recipient: Optional[str] = None) -> OTPProvider:
    if recipient and "@" in recipient:
        return EmailOTPProvider()

    provider_name = os.getenv("OTP_PROVIDER", "console").lower()
    if provider_name == "twilio":
        return TwilioOTPProvider()
    elif provider_name == "fast2sms":
        return Fast2SMSOTPProvider()
    elif provider_name == "email":
        return EmailOTPProvider()
    else:
        return ConsoleOTPProvider()


def send_file_share_link(recipient: str, filename: str, sender_name: str, share_url: str, reply_to: Optional[str] = None) -> bool:
    provider = get_otp_provider(recipient)
    if isinstance(provider, EmailOTPProvider):
        return provider.send_share_link(recipient, filename, sender_name, share_url, reply_to=reply_to)
    return provider.send_share_link(recipient, filename, sender_name, share_url)


def send_otp(recipient: str, otp_code: str, filename: Optional[str] = None) -> bool:
    provider = get_otp_provider(recipient)
    return provider.send_otp(recipient, otp_code, filename)


def generate_otp() -> str:
    """Generate a high-entropy 6-digit verification code."""
    return "".join(str(random.SystemRandom().randint(0, 9)) for _ in range(6))


def hash_otp(otp_code: str) -> str:
    """Hash the OTP code before storing it in the database using SHA-256."""
    return hashlib.sha256(otp_code.encode("utf-8")).hexdigest()

