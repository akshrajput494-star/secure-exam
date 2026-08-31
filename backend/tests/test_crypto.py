import pytest
import os
from app.services.crypto import generate_dek, encrypt_data, decrypt_data, encrypt_file, decrypt_file, compute_sha256, InvalidTag

def test_generate_dek_length():
    dek = generate_dek()
    assert len(dek) == 32

def test_generate_dek_randomness():
    dek1 = generate_dek()
    dek2 = generate_dek()
    assert dek1 != dek2

def test_encrypt_decrypt_roundtrip():
    dek = generate_dek()
    data = b"Secret Exam Content"
    ciphertext, nonce, tag = encrypt_data(dek, data)
    decrypted = decrypt_data(dek, ciphertext, nonce, tag)
    assert decrypted == data

def test_decrypt_tampered_ciphertext():
    dek = generate_dek()
    data = b"Secret Exam Content"
    ciphertext, nonce, tag = encrypt_data(dek, data)
    tampered_ciphertext = ciphertext[:-1] + b"X"
    
    with pytest.raises(InvalidTag):
        decrypt_data(dek, tampered_ciphertext, nonce, tag)

def test_decrypt_wrong_key():
    dek = generate_dek()
    wrong_dek = generate_dek()
    data = b"Secret Exam Content"
    ciphertext, nonce, tag = encrypt_data(dek, data)
    
    with pytest.raises(InvalidTag):
        decrypt_data(wrong_dek, ciphertext, nonce, tag)

def test_encrypt_file_roundtrip(tmp_path):
    dek = generate_dek()
    content = b"Mock PDF Content"
    
    input_file = tmp_path / "exam.pdf"
    enc_file = tmp_path / "exam.enc"
    dec_file = tmp_path / "exam_dec.pdf"
    
    input_file.write_bytes(content)
    
    nonce, tag = encrypt_file(dek, str(input_file), str(enc_file))
    decrypt_file(dek, str(enc_file), str(dec_file), nonce, tag)
    
    assert dec_file.read_bytes() == content

def test_compute_sha256():
    data = b"test"
    # echo -n "test" | sha256sum
    expected = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    assert compute_sha256(data) == expected

def test_nonce_uniqueness():
    dek = generate_dek()
    data = b"test data"
    _, nonce1, _ = encrypt_data(dek, data)
    _, nonce2, _ = encrypt_data(dek, data)
    assert nonce1 != nonce2
