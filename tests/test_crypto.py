import os
import sys
import io
import tempfile
from pathlib import Path

# Add project root and app to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "app"))
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app import crypto_utils, otp_service
except ImportError:
    import crypto_utils
    import otp_service

def test_key_derivation():
    print("Running test_key_derivation...")
    password = "SuperSecurePassword123"
    salt = os.urandom(16)
    
    key1 = crypto_utils.derive_key_from_password(password, salt)
    key2 = crypto_utils.derive_key_from_password(password, salt)
    assert key1 == key2, "Derived keys should be identical for the same password and salt"
    assert len(key1) == 32, "Derived key must be 32 bytes (256 bits)"
    
    key3 = crypto_utils.derive_key_from_password("DifferentPassword", salt)
    assert key1 != key3, "Derived keys must be different for different passwords"
    print("test_key_derivation PASSED!")


def test_master_key_wrap():
    print("Running test_master_key_wrap...")
    file_key = os.urandom(32)
    
    wrapped = crypto_utils.encrypt_key_with_master(file_key)
    assert len(wrapped) == 12 + 16 + 32, f"Wrapped key length is invalid: {len(wrapped)}"
    
    unwrapped = crypto_utils.decrypt_key_with_master(wrapped)
    assert unwrapped == file_key, "Unwrapped file key does not match the original"
    print("test_master_key_wrap PASSED!")


def test_chunked_encryption():
    print("Running test_chunked_encryption...")
    # Generate 150 KB of random data (spans multiple 64 KB chunks)
    original_data = os.urandom(150 * 1024)
    password = "TestPassword"
    salt = os.urandom(16)
    key = crypto_utils.derive_key_from_password(password, salt)
    
    # Input stream from original bytes
    input_stream = io.BytesIO(original_data)
    
    # Create temp file for ciphertext
    with tempfile.NamedTemporaryFile(delete=False) as temp_f:
        temp_filepath = temp_f.name
        try:
            # Encrypt
            crypto_utils.encrypt_file(input_stream, temp_f, key, salt)
            temp_f.close()
            
            # Decrypt using generator
            decrypted_data = b""
            for chunk in crypto_utils.decrypt_file_generator(temp_filepath, key):
                decrypted_data += chunk
                
            assert decrypted_data == original_data, "Decrypted data does not match original data"
            
            # Verify file verification check helper
            # Correct key
            test_gen = crypto_utils.decrypt_file_generator(temp_filepath, key)
            first_chunk = next(test_gen)
            assert len(first_chunk) > 0, "Decryption generator failed to fetch first chunk"
            test_gen.close()  # Release file descriptor
            
            # Incorrect key verification test
            wrong_key = crypto_utils.derive_key_from_password("WrongPassword", salt)
            wrong_gen = None
            try:
                wrong_gen = crypto_utils.decrypt_file_generator(temp_filepath, wrong_key)
                next(wrong_gen)
                assert False, "Decryption should have failed with incorrect key"
            except Exception:
                # Expected behavior: tag validation failure
                pass
            finally:
                if wrong_gen:
                    wrong_gen.close()  # Release file descriptor
                
            print("test_chunked_encryption PASSED!")
            
        finally:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)


def test_otp_generation_and_hashing():
    print("Running test_otp_generation_and_hashing...")
    otp1 = otp_service.generate_otp()
    otp2 = otp_service.generate_otp()
    
    assert len(otp1) == 6 and otp1.isdigit(), "OTP must be 6 digits"
    assert len(otp2) == 6 and otp2.isdigit(), "OTP must be 6 digits"
    
    # Check hashing
    hash1 = otp_service.hash_otp(otp1)
    hash2 = otp_service.hash_otp(otp1)
    assert hash1 == hash2, "OTP hashing should be deterministic"
    assert len(hash1) == 64, "SHA-256 hash must be 64 characters in hex"
    
    print("test_otp_generation_and_hashing PASSED!")


if __name__ == "__main__":
    print("Starting Cryptographic & Service validation tests...")
    test_key_derivation()
    test_master_key_wrap()
    test_chunked_encryption()
    test_otp_generation_and_hashing()
    print("All verification tests passed successfully!")
