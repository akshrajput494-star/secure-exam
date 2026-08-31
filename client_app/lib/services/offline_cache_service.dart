import 'dart:io';
import 'dart:typed_data';
import 'dart:convert';
import 'package:path_provider/path_provider.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:crypto/crypto.dart' as hash_util;
import 'crypto_service.dart';

/// Encrypted local cache for exam blobs supporting strict offline mode.
///
/// Stores encrypted exam PDFs in the app's secure document directory.
/// Each blob is stored with its SHA-256 checksum for integrity verification.
/// DEKs are stored separately in the Android Keystore via [FlutterSecureStorage].
///
/// Offline flow:
/// 1. Pre-download: encrypted exam blob cached locally via [cacheEncryptedExam]
/// 2. T-15 sync: DEK received via Kafka, stored via [CryptoService.storeDekSecurely]
/// 3. Exam time: blob decrypted locally — no network required
class OfflineCacheService {
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final CryptoService _cryptoService = CryptoService();

  /// Get the secure cache directory for encrypted exam blobs.
  Future<Directory> get _cacheDir async {
    final appDir = await getApplicationDocumentsDirectory();
    final cacheDir = Directory('${appDir.path}/secure_exam_cache');
    if (!await cacheDir.exists()) {
      await cacheDir.create(recursive: true);
    }
    return cacheDir;
  }

  /// Cache an encrypted exam blob locally for offline access.
  ///
  /// Stores the encrypted blob to disk and records metadata (SHA-256,
  /// download timestamp) in secure storage.
  Future<void> cacheEncryptedExam({
    required String examId,
    required Uint8List encryptedBlob,
    required String expectedSha256,
  }) async {
    // Verify integrity before caching
    final actualHash = hash_util.sha256.convert(encryptedBlob).toString();
    if (actualHash.toLowerCase() != expectedSha256.toLowerCase()) {
      throw Exception(
        'Integrity check failed: expected=$expectedSha256, actual=$actualHash',
      );
    }

    final dir = await _cacheDir;
    final file = File('${dir.path}/$examId.enc');
    await file.writeAsBytes(encryptedBlob, flush: true);

    // Store metadata in secure storage
    final metadata = jsonEncode({
      'sha256': expectedSha256,
      'cachedAt': DateTime.now().toIso8601String(),
      'sizeBytes': encryptedBlob.length,
    });
    await _secureStorage.write(key: 'cache_meta_$examId', value: metadata);
  }

  /// Check if an exam blob is cached locally and intact.
  Future<bool> isExamCached(String examId) async {
    final dir = await _cacheDir;
    final file = File('${dir.path}/$examId.enc');
    if (!await file.exists()) return false;

    // Verify integrity against stored hash
    final metaStr = await _secureStorage.read(key: 'cache_meta_$examId');
    if (metaStr == null) return false;

    final meta = jsonDecode(metaStr);
    final bytes = await file.readAsBytes();
    final actualHash = hash_util.sha256.convert(bytes).toString();
    return actualHash.toLowerCase() == (meta['sha256'] as String).toLowerCase();
  }

  /// Retrieve the cached encrypted blob for an exam.
  ///
  /// Returns null if not cached or integrity check fails.
  Future<Uint8List?> getCachedBlob(String examId) async {
    if (!await isExamCached(examId)) return null;
    final dir = await _cacheDir;
    final file = File('${dir.path}/$examId.enc');
    return file.readAsBytes();
  }

  /// Decrypt a cached exam using a previously received DEK.
  ///
  /// This is the core offline decryption flow:
  /// 1. Retrieves encrypted blob from local cache
  /// 2. Retrieves DEK from Android Keystore
  /// 3. Performs AES-256-GCM decryption locally
  /// 4. Returns plaintext PDF bytes (never written to disk)
  ///
  /// Throws if blob or DEK is not available.
  Future<Uint8List> decryptCachedExam(String examId) async {
    final encryptedBlob = await getCachedBlob(examId);
    if (encryptedBlob == null) {
      throw Exception('Exam $examId not found in local cache');
    }

    final dek = await _cryptoService.retrieveDek(examId);
    if (dek == null) {
      throw Exception('Decryption key not available for exam $examId');
    }

    try {
      final plaintext = _cryptoService.decryptExam(encryptedBlob, dek);
      return plaintext;
    } finally {
      // DEK remains in secure storage until explicitly cleared
      // after printing is confirmed
    }
  }

  /// Check if the decryption key is available for an exam.
  ///
  /// Returns true if the T-15 key sync has delivered the DEK.
  Future<bool> isDekAvailable(String examId) async {
    final dek = await _cryptoService.retrieveDek(examId);
    return dek != null;
  }

  /// Get cache metadata for an exam.
  Future<Map<String, dynamic>?> getCacheMetadata(String examId) async {
    final metaStr = await _secureStorage.read(key: 'cache_meta_$examId');
    if (metaStr == null) return null;
    return jsonDecode(metaStr);
  }

  /// Clear the cached blob and DEK for an exam after completion.
  ///
  /// Should be called after exam printing is confirmed to remove
  /// all sensitive material from the device.
  Future<void> clearExamCache(String examId) async {
    final dir = await _cacheDir;
    final file = File('${dir.path}/$examId.enc');
    if (await file.exists()) {
      // Overwrite with zeros before deleting (defense in depth)
      final length = await file.length();
      await file.writeAsBytes(Uint8List(length), flush: true);
      await file.delete();
    }
    await _secureStorage.delete(key: 'cache_meta_$examId');
    await _cryptoService.clearDek(examId);
  }

  /// Get total cache size in bytes.
  Future<int> getCacheSize() async {
    final dir = await _cacheDir;
    if (!await dir.exists()) return 0;
    int totalSize = 0;
    await for (final entity in dir.list()) {
      if (entity is File) {
        totalSize += await entity.length();
      }
    }
    return totalSize;
  }

  /// Clear all cached exams and keys.
  Future<void> clearAllCache() async {
    final dir = await _cacheDir;
    if (await dir.exists()) {
      await dir.delete(recursive: true);
    }
  }
}
