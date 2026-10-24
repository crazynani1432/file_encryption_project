import os
import struct
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

load_dotenv()

# Salt size and key size constants
SALT_SIZE = 16
NONCE_BASE_SIZE = 8
TAG_SIZE = 16
CHUNK_SIZE = 65536  # 64 KB

# Load SERVER_MASTER_KEY from env
SERVER_MASTER_KEY_HEX = os.getenv("SERVER_MASTER_KEY")
if SERVER_MASTER_KEY_HEX:
    try:
        SERVER_MASTER_KEY = bytes.fromhex(SERVER_MASTER_KEY_HEX)
        if len(SERVER_MASTER_KEY) != 32:
            raise ValueError("SERVER_MASTER_KEY must be exactly 32 bytes (64 hex characters)")
    except Exception as e:
        print(f"Error parsing SERVER_MASTER_KEY: {e}")
        SERVER_MASTER_KEY = os.urandom(32)  # Fallback to random ephemeral key in case of error
else:
    # Ephemeral key if not set
    print("Warning: SERVER_MASTER_KEY not set. Using ephemeral master key.")
    SERVER_MASTER_KEY = os.urandom(32)


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit AES key from a password and salt using PBKDF2-HMAC-SHA256.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_key_with_master(key: bytes) -> bytes:
    """
    Encrypt a file key using the Server Master Key.
    Returns: nonce (12 bytes) + tag (16 bytes) + ciphertext
    """
    aesgcm = AESGCM(SERVER_MASTER_KEY)
    nonce = os.urandom(12)
    # Encrypt key (32 bytes)
    ciphertext_with_tag = aesgcm.encrypt(nonce, key, None)
    # The return from cryptography's AESGCM.encrypt is ciphertext + tag concatenated.
    # We can just return nonce + ciphertext_with_tag
    return nonce + ciphertext_with_tag


def decrypt_key_with_master(wrapped_key: bytes) -> bytes:
    """
    Decrypt an encrypted file key using the Server Master Key.
    """
    if len(wrapped_key) < 28:  # 12 nonce + 16 tag
        raise ValueError("Invalid wrapped key size")
    
    aesgcm = AESGCM(SERVER_MASTER_KEY)
    nonce = wrapped_key[:12]
    ciphertext_with_tag = wrapped_key[12:]
    
    return aesgcm.decrypt(nonce, ciphertext_with_tag, None)


def encrypt_file(input_stream, output_stream, key: bytes, salt: bytes) -> None:
    """
    Encrypts an input byte stream into an output stream using chunked AES-256-GCM.
    Write Header: Salt (16 bytes) + Base Nonce (8 bytes)
    Write Chunks: Length (4 bytes, Big-Endian) + Tag (16 bytes) + Ciphertext (N bytes)
    """
    # Write salt to output
    output_stream.write(salt)
    
    # Generate 8-byte base nonce
    base_nonce = os.urandom(NONCE_BASE_SIZE)
    output_stream.write(base_nonce)
    
    aesgcm = AESGCM(key)
    chunk_index = 0
    
    while True:
        chunk = input_stream.read(CHUNK_SIZE)
        if not chunk:
            break
            
        # Derive chunk-specific 12-byte nonce
        # base_nonce (8 bytes) + chunk_index (4 bytes big-endian)
        chunk_nonce = base_nonce + struct.pack(">I", chunk_index)
        
        # Encrypt the chunk
        encrypted_data = aesgcm.encrypt(chunk_nonce, chunk, None)
        
        # In cryptography's AESGCM, encrypted_data is ciphertext followed by 16-byte tag.
        # Let's separate them: ciphertext is encrypted_data[:-16], tag is encrypted_data[-16:]
        tag = encrypted_data[-TAG_SIZE:]
        ciphertext = encrypted_data[:-TAG_SIZE]
        
        # Write format: [4 bytes ciphertext length] [16 bytes tag] [ciphertext]
        output_stream.write(struct.pack(">I", len(ciphertext)))
        output_stream.write(tag)
        output_stream.write(ciphertext)
        
        chunk_index += 1


def decrypt_file_generator(filepath: str, key: bytes):
    """
    A generator that reads an encrypted file and yields decrypted chunks.
    Raises ValueError or cryptography.exceptions.InvalidTag if decryption fails.
    """
    aesgcm = AESGCM(key)
    
    with open(filepath, "rb") as f:
        # Read salt and base nonce
        salt = f.read(SALT_SIZE)
        if len(salt) < SALT_SIZE:
            raise ValueError("Corrupt file: cannot read salt")
            
        base_nonce = f.read(NONCE_BASE_SIZE)
        if len(base_nonce) < NONCE_BASE_SIZE:
            raise ValueError("Corrupt file: cannot read base nonce")
            
        chunk_index = 0
        
        while True:
            # Read chunk length (4 bytes)
            length_bytes = f.read(4)
            if not length_bytes:
                break  # End of file
                
            if len(length_bytes) < 4:
                raise ValueError("Corrupt file: invalid chunk header")
                
            ciphertext_length = struct.unpack(">I", length_bytes)[0]
            
            # Read tag (16 bytes)
            tag = f.read(TAG_SIZE)
            if len(tag) < TAG_SIZE:
                raise ValueError("Corrupt file: missing tag")
                
            # Read ciphertext
            ciphertext = f.read(ciphertext_length)
            if len(ciphertext) < ciphertext_length:
                raise ValueError("Corrupt file: missing ciphertext data")
                
            # Reconstruct the 12-byte nonce for this chunk
            chunk_nonce = base_nonce + struct.pack(">I", chunk_index)
            
            # Reassemble ciphertext + tag for cryptography library
            encrypted_data = ciphertext + tag
            
            # Decrypt
            decrypted_chunk = aesgcm.decrypt(chunk_nonce, encrypted_data, None)
            yield decrypted_chunk
            
            chunk_index += 1
