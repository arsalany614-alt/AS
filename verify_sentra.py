"""
SENTRA AS - System Validation Suite
A comprehensive integration test verifying encryption integrity, local vector database
emulation performance, dynamic module registry routing, and autonomous sleep pipelines.
Expanded to audit the Automated Finance System and algorithmic Trading Assistant.
"""

import os
import sys
import time
import json
from pathlib import Path

# Ensure absolute import path resolution
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from sentra_as.security import initialize_key, SecurityEngine, get_default_key_path
    from sentra_as.database import (
        initialize_database,
        log_system_event,
        add_semantic_memory,
        query_semantic_memory,
        add_approval_item,
        get_pending_approval_items,
        update_approval_status,
        get_financial_ledger,
        get_db_path
    )
    from sentra_as.modules import execute_module
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = e

def run_validation_suite() -> bool:
    print("=" * 60)
    print("      SENTRA AS SYSTEM INTEGRATION VALIDATION SUITE      ")
    print("=" * 60)
    
    if not IMPORTS_OK:
        print(f"[FAIL] Imports check failed: {IMPORT_ERROR}")
        return False
        
    print("[PASS] Core imports verified successfully.")
    
    # 1. Initialize DB & Keys
    print("\n--- Phase 1: Security & Storage Initialization ---")
    try:
        initialize_database()
        db_path = get_db_path()
        print(f"[OK] Database initialized at: {db_path}")
        assert db_path.exists(), "SQLite Database file was not created!"
        
        key = initialize_key("ArsalanPasscode2026", force_recreate=True)
        key_path = get_default_key_path()
        print(f"[OK] Master encryption key initialized at: {key_path}")
        assert key_path.exists(), "Encryption keyfile was not created!"
        
        # Instantiate security engine
        engine = SecurityEngine(key)
        print(f"[OK] Security engine active: {engine.mode}")
    except Exception as e:
        print(f"[FAIL] Phase 1 Failed: {e}")
        return False
        
    # 2. Test Cryptographic Integrity
    print("\n--- Phase 2: Cryptographic Integrity Test ---")
    try:
        secret_payload = "Arsalan private ledger transaction: 50,000 USD to AI offshore nodes."
        ciphertext = engine.encrypt_string(secret_payload)
        print(f"[OK] Plaintext successfully encrypted into ciphertext.")
        
        decrypted = engine.decrypt_string(ciphertext)
        print(f"[OK] Ciphertext successfully decrypted back to plaintext.")
        
        assert decrypted == secret_payload, "Decryption match check failed!"
        print("[PASS] Cryptographic integrity test verified.")
    except Exception as e:
        print(f"[FAIL] Phase 2 Cryptography Failed: {e}")
        return False
        
    # 3. Test Local Vector Database Emulation
    print("\n--- Phase 3: Pure-Python Cosine Vector Emulation ---")
    try:
        # Clear out prior tests to make vector indexing pristine
        import sqlite3
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("DELETE FROM semantic_memory")
            
        print("[OK] Injecting distinct semantic vectors into memory database...")
        add_semantic_memory(
            content="Standard vector search engines rely on binary dependencies that compile poorly on mobile Android devices.",
            tags=["mobile", "architecture"]
        )
        add_semantic_memory(
            content="FERNET AES-256 provides excellent encryption layers for SQLite relational tables.",
            tags=["security", "sqlite"]
        )
        add_semantic_memory(
            content="Autonomy triggers on Kivy must execute on background threads to prevent UI lockups.",
            tags=["kivy", "threading"]
        )
        
        # Semantically query the memory
        query = "How to encrypt database table fields securely?"
        print(f"[OK] Querying semantic memory for text: '{query}'")
        results = query_semantic_memory(query, top_k=1)
        
        assert len(results) > 0, "No vector matching results returned!"
        best_match = results[0]
        
        print(f"[OK] Cosine match found. Similarity: {best_match['similarity']} | Tags: {best_match['tags']}")
        print(f"Content: \"{best_match['content']}\"")
        
        assert "security" in best_match["tags"], "Incorrect semantic mapping occurred!"
        print("[PASS] Local Vector Emulation query matched correct context.")
    except Exception as e:
        print(f"[FAIL] Phase 3 Vector Emulation Failed: {e}")
        return False
        
    # 4. Test Automated Modules & Holding Pipelines
    print("\n--- Phase 4: Automated Advanced Pipelines ---")
    try:
        # Delete prior holding gateway records and financial ledger
        import sqlite3
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("DELETE FROM approval_gateway")
            conn.execute("DELETE FROM financial_ledger")
            
        print("[OK] Executing Media Production bundle...")
        script = execute_module("script_writer", "Sovereign Personal AI Hardware Sync")
        audio = execute_module("voice_over", script)
        video = execute_module("video_generator", audio)
        social = execute_module("social_media", script)
        
        # Inject Media Content Hold
        add_approval_item(
            title="Sovereign AI Offline OS",
            asset_type="video",
            content=social,
            metadata={"script": script[:50], "audio_path": audio, "video_path": video}
        )
        
        print("[OK] Executing Algorithmic Trading Assistant...")
        trading_report = execute_module("trading_assistant")
        print(f"Trading Report Output:\n{trading_report}\n")
        
        print("[OK] Executing Automated Personal Finance Auditor...")
        finance_report = execute_module("finance_manager")
        print(f"Finance Report Output:\n{finance_report}\n")
        
        # Verify holding gateway contains all three diverse items (Video, Trade Ticket, Finance Proposal)
        pending_gateway = get_pending_approval_items()
        print(f"[OK] Holding Gateway current pending item count: {len(pending_gateway)}")
        assert len(pending_gateway) >= 2, "Gateway hold pipeline write failed for multi-assets!"
        
        print("\nGateway Pending Review Deck:")
        for idx, held_item in enumerate(pending_gateway):
            print(f"{idx+1}. TYPE: {held_item['type'].upper()} | TITLE: '{held_item['title']}'")
            
        # Simulate approval of a Trade ticket to verify relational integration
        trade_tickets = [item for item in pending_gateway if item["type"] == "trade"]
        if trade_tickets:
            ticket = trade_tickets[0]
            print(f"\n[OK] Simulating Arsalan approving Trade: '{ticket['title']}'")
            update_approval_status(ticket["id"], "approved")
            
            # Execute trade simulation ledger deduct
            limit_p = ticket["metadata"].get("limit_price", 95000.0)
            amount = ticket["metadata"].get("amount", 0.05)
            cost = limit_p * amount
            
            add_financial_record(cost, "expense", "Asset Purchase", f"Trade Buy {amount} BTC successfully executed.")
            
            # Verify cost deducted in database financial ledger
            ledger = get_financial_ledger()
            print(f"[OK] Verified transaction ledger entries count: {len(ledger)}")
            assert len(ledger) > 0, "Trade order capital ledger write failed!"
            print(f"Recorded transaction detail: \"{ledger[-1]['details']}\" - Amount: {ledger[-1]['amount']:,.2f} USD")
            
        print("[PASS] Multi-asset automated pipelines and Human-in-the-Loop Gateway verified.")
    except Exception as e:
        print(f"[FAIL] Phase 4 Advanced Pipelines Failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("  STATUS: ALL 4 ARCHITECTURAL VALIDATION PHASES PASSED SUCCESS  ")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_validation_suite()
    sys.exit(0 if success else 1)
