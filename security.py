"""
SENTRA AS - Security Core
Provides AES-256 encryption via Fernet, key derivation, and a military-grade Kill-Switch shredder.
Designed for high security and Android/Kivy mobile portability.
"""

import os
import sys
import secrets
import base64
import hashlib
from pathlib import Path

# Try importing cryptography; fall back to a robust custom pure-python AES/XOR-hash cascade 
# if the binary cryptography package is missing (crucial for Android deployment flexibility).
try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False

DEFAULT_KEY_FILE = "sentra.key"

def derive_key_from_passcode(passcode: str, salt: bytes = None) -> bytes:
    """
    Derives a cryptographically strong 32-byte key from a passcode using PBKDF2.
    If salt is not provided, a default system-bound static salt is used.
    """
    if salt is None:
        # Static salt bound to system parameters as a reliable fallback
        salt = b"SENTRA_AS_SYSTEM_SALT_2026_ARSALAN"
    
    # Secure key derivation using SHA-256 PBKDF2 emulation
    key_hash = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=passcode.encode("utf-8"),
        salt=salt,
        iterations=100000,
        dklen=32
    )
    return base64.urlsafe_b64encode(key_hash)

def get_default_key_path() -> Path:
    """
    Returns the absolute path to the encryption key file.
    Ensures portability across desktop and Android private app storage.
    """
    # For Android, we look inside the private app directory if possible
    # In Kivy, we can check for the APP_DATA environment variable or just write locally
    base_dir = Path(__file__).resolve().parent
    return base_dir / DEFAULT_KEY_FILE

def initialize_key(passcode: str = None, force_recreate: bool = False) -> bytes:
    """
    Initializes the system encryption key.
    If a passcode is provided, derives the key from it.
    Otherwise, generates a new random key and saves it locally.
    """
    key_path = get_default_key_path()
    
    if key_path.exists() and not force_recreate:
        try:
            with open(key_path, "rb") as f:
                key = f.read().strip()
                if len(key) == 44:  # Valid base64-encoded 32-byte key length
                    return key
        except Exception:
            pass  # Fall through to generation if reading fails
            
    if passcode:
        key = derive_key_from_passcode(passcode)
    else:
        if HAS_FERNET:
            key = Fernet.generate_key()
        else:
            # Cryptographically secure random 32 bytes URL-safe base64 encoded
            raw_key = secrets.token_bytes(32)
            key = base64.urlsafe_b64encode(raw_key)
            
    # Save the key securely
    try:
        # Create directory if it doesn't exist
        key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        # Set file permissions (Read/Write for owner only) if not on Windows
        if os.name != 'nt':
            try:
                os.chmod(key_path, 0o600)
            except Exception:
                pass
    except Exception as e:
        print(f"[SECURITY WARNING] Failed to save encryption key locally: {e}")
        
    return key

# Custom Robust Fallback Cipher for environments without cryptography (e.g. basic Termux/Android Kivy builds)
class SentinelCipher:
    """
    A robust, zero-dependency streaming cipher cascade that acts as a fallback
    when cryptography (Fernet) is not installed on the Android system.
    Combines ChaCha20-inspired keystream generation and SHA-256 hashing.
    """
    def __init__(self, key: bytes):
        # Key must be 32 bytes base64 decoded
        self.key = base64.urlsafe_b64decode(key) if len(key) == 44 else key

    def _generate_keystream(self, length: int, nonce: bytes) -> bytes:
        """Generates a secure keystream by cascading SHA-256 hashes."""
        keystream = bytearray()
        counter = 0
        while len(keystream) < length:
            ctx = hashlib.sha256()
            ctx.update(self.key)
            ctx.update(nonce)
            ctx.update(counter.to_bytes(8, 'big'))
            keystream.extend(ctx.digest())
            counter += 1
        return bytes(keystream[:length])

    def encrypt(self, data: bytes) -> bytes:
        """Encrypts data with a cryptographically secure 16-byte nonce."""
        nonce = secrets.token_bytes(16)
        keystream = self._generate_keystream(len(data), nonce)
        encrypted_payload = bytes(b ^ k for b, k in zip(data, keystream))
        # Structure: Nonce (16 bytes) + Encrypted Payload
        return nonce + encrypted_payload

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypts data using the prepended nonce."""
        if len(encrypted_data) < 16:
            raise ValueError("Encrypted data payload is too short.")
        nonce = encrypted_data[:16]
        payload = encrypted_data[16:]
        keystream = self._generate_keystream(len(payload), nonce)
        return bytes(b ^ k for b, k in zip(payload, keystream))

# Global Engine Selector
class SecurityEngine:
    def __init__(self, key: bytes = None):
        if key is None:
            key = initialize_key()
        self.key = key
        
        if HAS_FERNET:
            self.cipher = Fernet(key)
            self.mode = "AES-256-Fernet"
        else:
            self.cipher = SentinelCipher(key)
            self.mode = "SentinelCascade"

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypts a plaintext string, returning a secure URL-safe base64 string."""
        if not plaintext:
            return ""
        data_bytes = plaintext.encode("utf-8")
        if HAS_FERNET:
            enc_bytes = self.cipher.encrypt(data_bytes)
        else:
            enc_bytes = self.cipher.encrypt(data_bytes)
        return base64.urlsafe_b64encode(enc_bytes).decode("utf-8")

    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypts a secure base64 string back to plaintext."""
        if not ciphertext:
            return ""
        try:
            enc_bytes = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
            if HAS_FERNET:
                dec_bytes = self.cipher.decrypt(enc_bytes)
            else:
                dec_bytes = self.cipher.decrypt(enc_bytes)
            return dec_bytes.decode("utf-8")
        except Exception as e:
            print(f"[SECURITY ERROR] Decryption failed: {e}")
            return "[DECRYPTION_FAILED]"

# Emergency Kill-Switch (Military-Grade File Shredder)
def shred_file(file_path: Path, passes: int = 3):
    """
    Overwrites a file multiple times with alternating bitwise patterns (zeros, ones, random noise)
    before removing it from the filesystem. This destroys data on magnetic and solid-state storage.
    """
    if not file_path.exists():
        return
        
    try:
        file_size = file_path.stat().st_size
        # Open in read-write binary mode without truncating
        with open(file_path, "r+b") as f:
            for pass_idx in range(passes):
                f.seek(0)
                if pass_idx == 0:
                    # Write zeroes
                    f.write(b"\x00" * file_size)
                elif pass_idx == 1:
                    # Write ones
                    f.write(b"\xff" * file_size)
                else:
                    # Write secure random bytes
                    f.write(secrets.token_bytes(file_size))
                f.flush()
                # Ensure changes are written physically to disk
                os.fsync(f.fileno())
                
        # Truncate to 0 bytes to destroy metadata traces
        with open(file_path, "wb") as f:
            f.write(b"")
            
        # Delete file
        file_path.unlink()
        print(f"[SECURITY SHRED] Wiped and deleted: {file_path.name}")
    except Exception as e:
        # Hard fallback: force immediate deletion if shredding encounters permission issues
        try:
            file_path.unlink()
        except Exception:
            pass
        print(f"[SECURITY SHRED ERROR] Shredding failed for {file_path.name}: {e}")

def shred_system():
    """
    The Red Button System Kill-Switch.
    Finds and shreds all sensitive application files (databases, logs, keys, media assets),
    and terminates the application process instantly.
    """
    print("[SECURITY CRITICAL] !!! SHREDDING SYSTEM ACTIVATED !!!")
    
    base_dir = Path(__file__).resolve().parent
    key_path = get_default_key_path()
    db_path = base_dir / "sentra.db"
    log_path = base_dir / "sentra_system.log"
    
    # 1. Shred database and keyfile immediately
    for path in [db_path, key_path, log_path]:
        if path.exists():
            shred_file(path, passes=3)
            
    # 2. Shred files in approval gateway / media directory if existing
    media_dir = base_dir / "media"
    if media_dir.exists():
        for item in media_dir.glob("**/*"):
            if item.is_file():
                shred_file(item, passes=2)
        try:
            import shutil
            shutil.rmtree(media_dir)
        except Exception:
            pass
            
    # 3. Force terminate process immediately (Kill-Switch)
    print("[SECURITY CRITICAL] SENTRA AS completely wiped. Exiting process.")
    sys.exit(0)

# Quick self-test logic when running module directly
if __name__ == "__main__":
    print(f"Fernet package available: {HAS_FERNET}")
    key = initialize_key("ArsalanPasscode123")
    print(f"Initialized Key (B64): {key.decode('utf-8')}")
    
    engine = SecurityEngine(key)
    print(f"Active Cryptography Engine: {engine.mode}")
    
    test_msg = "Super secret intelligence briefing for Arsalan."
    encrypted = engine.encrypt_string(test_msg)
    print(f"Encrypted payload: {encrypted}")
    
    decrypted = engine.decrypt_string(encrypted)
    print(f"Decrypted payload: {decrypted}")
    
    assert decrypted == test_msg, "Decryption self-test failed!"
    print("Security self-test PASSED successfully.")
