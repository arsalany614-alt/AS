"""
SENTRA AS - Database Core & Local Vector Emulation
Provides secure SQL storage and a high-performance, pure-Python vector search core
designed for 100% offline compatibility and thread-safety on Android mobile devices.
"""

import os
import sqlite3
import json
import time
import math
import hashlib
import threading
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Fix: Handled local import path for Android compatibility
try:
    from security import SecurityEngine, initialize_key
except ImportError:
    from sentra_as.security import SecurityEngine, initialize_key

DB_FILE = "sentra.db"
db_lock = threading.Lock()

def get_db_path() -> Path:
    """Returns the absolute path to the SQLite database."""
    base_dir = Path(__file__).resolve().parent
    return base_dir / DB_FILE

class SafeDatabaseConnection:
    """
    A thread-safe, context-managed SQLite connection wrapper.
    Ensures safe concurrency in Kivy background threads by utilizing a global Lock,
    preventing SQLite locking errors on Android.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def __enter__(self):
        db_lock.acquire()
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return self.cursor
        except Exception as e:
            db_lock.release()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            if self.conn:
                self.conn.close()
            db_lock.release()

# --- Pure-Python Deterministic Vector Emulation Core ---

def generate_local_embedding(text: str, dimensions: int = 128) -> List[float]:
    """
    Generates a deterministic 128-dimensional unit vector from input text.
    Uses an advanced hashing trick combining word-level hashes and character-trigram hashes.
    Provides semantic-like lexical alignment for offline search, requiring 0 heavy ML libraries.
    """
    if not text:
        return [0.0] * dimensions
        
    vector = [0.0] * dimensions
    text = text.lower()
    
    words = text.split()
    for word in words:
        if len(word) < 2 and word not in ("a", "i"):
            continue
        for salt in (b"w1", b"w2"):
            h = hashlib.sha256(word.encode("utf-8") + salt).digest()
            idx = int.from_bytes(h[:4], "big") % dimensions
            weight = math.log1p(len(word))
            vector[idx] += weight

    if len(text) >= 3:
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            h = hashlib.sha256(trigram.encode("utf-8") + b"tg").digest()
            idx = int.from_bytes(h[:4], "big") % dimensions
            vector[idx] += 0.5

    sq_sum = sum(x * x for x in vector)
    if sq_sum > 0:
        norm = math.sqrt(sq_sum)
        vector = [x / norm for x in vector]
    else:
        vector[0] = 1.0
        
    return vector

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if len(v1) != len(v2):
        return 0.0
    return sum(a * b for a, b in zip(v1, v2))

# --- Database Initialization & Operations ---

def initialize_database():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                component TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_enc TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                tags TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                details_enc TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_type TEXT NOT NULL,
                action_module TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_gateway (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                content_enc TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_enc TEXT NOT NULL
            )
        """)

_key = initialize_key()
security_engine = SecurityEngine(_key)

def log_system_event(component: str, payload: str):
    db_path = get_db_path()
    timestamp = time.time()
    try:
        with SafeDatabaseConnection(db_path) as cursor:
            cursor.execute(
                "INSERT INTO system_logs (timestamp, component, payload) VALUES (?, ?, ?)",
                (timestamp, component, payload)
            )
    except Exception as e:
        print(f"[DB ERROR] Log system event failed: {e}")

def add_semantic_memory(content: str, tags: List[str], custom_vector: List[float] = None):
    db_path = get_db_path()
    enc_content = security_engine.encrypt_string(content)
    
    if custom_vector is None:
        vector = generate_local_embedding(content)
    else:
        vector = custom_vector
        
    vector_json = json.dumps(vector)
    tags_str = ",".join(tags)
    
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute(
            "INSERT INTO semantic_memory (content_enc, vector_json, tags) VALUES (?, ?, ?)",
            (enc_content, vector_json, tags_str)
        )
    log_system_event("MEMORY_SYSTEM", f"Stored encrypted semantic memory under tags: {tags_str}")

def query_semantic_memory(query_text: str, top_k: int = 3, threshold: float = 0.1) -> List[Dict[str, Any]]:
    db_path = get_db_path()
    query_vector = generate_local_embedding(query_text)
    matches: List[Tuple[float, Dict[str, Any]]] = []
    
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute("SELECT id, content_enc, vector_json, tags FROM semantic_memory")
        rows = cursor.fetchall()
        
        for row in rows:
            try:
                decrypted_content = security_engine.decrypt_string(row["content_enc"])
                stored_vector = json.loads(row["vector_json"])
                tags = row["tags"].split(",") if row["tags"] else []
                similarity = cosine_similarity(query_vector, stored_vector)
                
                if similarity >= threshold:
                    matches.append((similarity, {
                        "id": row["id"],
                        "content": decrypted_content,
                        "tags": tags,
                        "similarity": round(similarity, 4)
                    }))
            except Exception:
                continue
                
    matches.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in matches[:top_k]]

def add_financial_record(amount: float, record_type: str, category: str, details: str):
    db_path = get_db_path()
    enc_details = security_engine.encrypt_string(details)
    
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute(
            "INSERT INTO financial_ledger (amount, type, category, details_enc) VALUES (?, ?, ?, ?)",
            (amount, record_type, category, enc_details)
        )
    log_system_event("FINANCIAL_MANAGER", f"Inserted secure financial transaction under category: {category}")

def get_financial_ledger() -> List[Dict[str, Any]]:
    db_path = get_db_path()
    records = []
    
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute("SELECT id, amount, type, category, details_enc FROM financial_ledger")
        rows = cursor.fetchall()
        for row in rows:
            try:
                details = security_engine.decrypt_string(row["details_enc"])
                records.append({
                    "id": row["id"],
                    "amount": row["amount"],
                    "type": row["type"],
                    "category": row["category"],
                    "details": details
                })
            except Exception:
                continue
    return records

def add_automation_rule(trigger_type: str, action_module: str, active: int = 1):
    db_path = get_db_path()
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute(
            "INSERT INTO automation_rules (trigger_type, action_module, active) VALUES (?, ?, ?)",
            (trigger_type, action_module, active)
        )
    log_system_event("AUTOMATION_ENGINE", f"Registered automation rule: Trigger={trigger_type} -> Module={action_module}")

def get_active_automation_rules() -> List[Dict[str, Any]]:
    db_path = get_db_path()
    rules = []
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute("SELECT id, trigger_type, action_module, active FROM automation_rules WHERE active = 1")
        rows = cursor.fetchall()
        for row in rows:
            rules.append({
                "id": row["id"],
                "trigger_type": row["trigger_type"],
                "action_module": row["action_module"],
                "active": bool(row["active"])
            })
    return rules

def add_approval_item(title: str, asset_type: str, content: str, metadata: Dict[str, Any] = None):
    db_path = get_db_path()
    timestamp = time.time()
    enc_content = security_engine.encrypt_string(content)
    metadata_str = json.dumps(metadata if metadata else {})
    enc_metadata = security_engine.encrypt_string(metadata_str)
    
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute(
            """INSERT INTO approval_gateway
               (timestamp, title, type, content_enc, status, metadata_enc)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (timestamp, title, asset_type, enc_content, enc_metadata)
        )
    log_system_event("APPROVAL_GATEWAY", f"New pending asset hold: '{title}' ({asset_type})")

def get_pending_approval_items() -> List[Dict[str, Any]]:
    db_path = get_db_path()
    items = []
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute(
            "SELECT id, timestamp, title, type, content_enc, status, metadata_enc FROM approval_gateway WHERE status = 'pending'"
        )
        rows = cursor.fetchall()
        for row in rows:
            try:
                content = security_engine.decrypt_string(row["content_enc"])
                meta_json = security_engine.decrypt_string(row["metadata_enc"])
                metadata = json.loads(meta_json)
                items.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "title": row["title"],
                    "type": row["type"],
                    "content": content,
                    "status": row["status"],
                    "metadata": metadata
                })
            except Exception as e:
                print(f"[DB ERROR] Failed decrypting approval item {row['id']}: {e}")
                continue
    return items

def update_approval_status(item_id: int, status: str):
    db_path = get_db_path()
    if status not in ("approved", "discarded", "pending"):
        raise ValueError(f"Invalid approval status: {status}")
    with SafeDatabaseConnection(db_path) as cursor:
        cursor.execute(
            "UPDATE approval_gateway SET status = ? WHERE id = ?",
            (status, item_id)
        )
    log_system_event("APPROVAL_GATEWAY", f"Asset ID {item_id} updated to state: {status}")

if __name__ == "__main__":
    initialize_database()
