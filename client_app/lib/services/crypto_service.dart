import 'dart:typed_data';
import 'dart:convert';
import 'package:pointycastle/export.dart' as pc;
import 'package:crypto/crypto.dart' as crypto;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class CryptoService {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  // AES-256-GCM decryption
  // Format: nonce (12 bytes) || ciphertext || tag (16 bytes)
  Uint8List decryptExam(Uint8List encryptedBlob, Uint8List dek) {
    if (encryptedBlob.length < 28) {
      throw Exception('Invalid encrypted data format');
    }

    final nonce = encryptedBlob.sublist(0, 12);
    final ciphertextWithTag = encryptedBlob.sublist(12);

    final cipher = pc.GCMBlockCipher(pc.AESEngine())
      ..init(
        false, // false = decrypt
        pc.AEADParameters(
          pc.KeyParameter(dek),
          128, // tag size in bits
          nonce,
          Uint8List(0), // AAD
        ),
      );

    final decrypted = cipher.process(ciphertextWithTag);
    return decrypted;
  }

  Future<void> storeDekSecurely(String examId, Uint8List dek) async {
    final dekBase64 = base64Encode(dek);
    await _storage.write(key: 'dek_$examId', value: dekBase64);
  }

  Future<Uint8List?> retrieveDek(String examId) async {
    final dekBase64 = await _storage.read(key: 'dek_$examId');
    if (dekBase64 != null) {
      return base64Decode(dekBase64);
    }
    return null;
  }

  Future<void> clearDek(String examId) async {
    await _storage.delete(key: 'dek_$examId');
  }

  bool verifySha256(Uint8List data, String expectedHash) {
    final digest = crypto.sha256.convert(data);
    final actualHash = digest.toString();
    return actualHash.toLowerCase() == expectedHash.toLowerCase();
  }
}
