#!/usr/bin/env python3
"""
Test utility to generate a sample PDF exam, encrypt it, and store it.
Useful for manual testing of the full pipeline.
"""

import os
import sys
import uuid
import asyncio

try:
    from reportlab.pdfgen import canvas
except ImportError:
    print("reportlab not installed. Run: pip install reportlab")
    sys.exit(1)

# Adjust path to import from backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from app.crypto.engine import CryptoEngine
except ImportError:
    print("Could not import app.crypto.engine. Ensure you are in the correct environment and backend is set up.")
    # Dummy mock for standalone execution without backend
    class CryptoEngine:
        def __init__(self, key_id):
            pass
        def encrypt_file(self, data):
            return b"ENCRYPTED_" + data, b"WRAPPED_DEK", b"IV", b"TAG"

def generate_pdf(filepath: str) -> bytes:
    """Generate a simple PDF file in memory (or save to disk and read)."""
    c = canvas.Canvas(filepath)
    c.drawString(100, 750, "CONFIDENTIAL EXAM")
    c.drawString(100, 730, "Do not distribute. This exam is secured.")
    c.drawString(100, 700, "1. What is the capital of France?")
    c.drawString(100, 680, "2. Explain the theory of relativity.")
    c.save()
    
    with open(filepath, 'rb') as f:
        return f.read()

async def main():
    print("=== Generate Test Exam ===")
    
    exam_id = str(uuid.uuid4())
    print(f"Exam ID: {exam_id}")
    
    # Ensure storage dir exists
    storage_dir = os.path.join(os.path.dirname(__file__), '..', 'storage', 'encrypted_exams')
    os.makedirs(storage_dir, exist_ok=True)
    
    raw_pdf_path = os.path.join(storage_dir, f"{exam_id}_raw.pdf")
    enc_pdf_path = os.path.join(storage_dir, f"{exam_id}.encrypted")
    
    print("Generating raw PDF...")
    pdf_data = generate_pdf(raw_pdf_path)
    
    print("Encrypting PDF with CryptoEngine...")
    try:
        # Assuming kms_key_id is passed or configured
        engine = CryptoEngine(kms_key_id=os.getenv("AWS_KMS_KEY_ID", "mock-key-id"))
        
        # This assumes encrypt_file is async or sync. Adjust based on actual implementation.
        # If it's sync:
        encrypted_data, wrapped_dek, iv, tag = engine.encrypt_file(pdf_data)
        
        with open(enc_pdf_path, 'wb') as f:
            f.write(encrypted_data)
        
        print("Encryption successful.")
        print(f"Raw file (DO NOT DISTRIBUTE): {raw_pdf_path}")
        print(f"Encrypted blob: {enc_pdf_path}")
        print(f"Wrapped DEK (hex): {wrapped_dek.hex() if isinstance(wrapped_dek, bytes) else wrapped_dek}")
        
    except Exception as e:
        print(f"Encryption failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
