import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';
import '../models/exam_model.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  final http.Client _client = http.Client();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _jwtToken;

  ApiService();

  Future<Map<String, String>> _getHeaders() async {
    _jwtToken ??= await _storage.read(key: 'jwt_token');
    return {
      'Content-Type': 'application/json',
      if (_jwtToken != null) 'Authorization': 'Bearer $_jwtToken',
    };
  }

  Future<void> login(String email, String password) async {
    final response = await _client.post(
      Uri.parse('${AppConfig.apiBaseUrl}/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    ).timeout(AppConfig.apiTimeout);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _jwtToken = data['token'];
      await _storage.write(key: 'jwt_token', value: _jwtToken);
    } else {
      throw Exception('Login failed: ${response.body}');
    }
  }

  Future<List<ExamModel>> fetchExams() async {
    final headers = await _getHeaders();
    final response = await _client.get(
      Uri.parse('${AppConfig.apiBaseUrl}/exams'),
      headers: headers,
    ).timeout(AppConfig.apiTimeout);

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => ExamModel.fromJson(json)).toList();
    } else if (response.statusCode == 401) {
      // Need refresh logic here
      throw Exception('Unauthorized');
    } else {
      throw Exception('Failed to fetch exams');
    }
  }

  Future<Uint8List> downloadEncryptedExam(String examId) async {
    final headers = await _getHeaders();
    final response = await _client.get(
      Uri.parse('${AppConfig.apiBaseUrl}/exams/$examId/download'),
      headers: headers,
    ).timeout(AppConfig.apiTimeout);

    if (response.statusCode == 200) {
      return response.bodyBytes;
    } else {
      throw Exception('Failed to download exam');
    }
  }

  Future<String> verifyBiometric(String superintendentId, String challengeToken, String deviceFingerprint) async {
    final headers = await _getHeaders();
    final response = await _client.post(
      Uri.parse('${AppConfig.apiBaseUrl}/auth/biometric'),
      headers: headers,
      body: jsonEncode({
        'superintendentId': superintendentId,
        'challengeToken': challengeToken,
        'deviceFingerprint': deviceFingerprint,
      }),
    ).timeout(AppConfig.apiTimeout);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['sessionToken'];
    } else {
      throw Exception('Biometric verification failed at server');
    }
  }

  Future<void> reportAuditEvent(String action, Map<String, dynamic> metadata) async {
    final headers = await _getHeaders();
    final entry = AuditEntry(action: action, timestamp: DateTime.now(), metadata: metadata);
    try {
      await _client.post(
        Uri.parse('${AppConfig.apiBaseUrl}/audit'),
        headers: headers,
        body: jsonEncode(entry.toJson()),
      ).timeout(AppConfig.apiTimeout);
    } catch (e) {
      // Log failure but don't crash app for audit errors
      print('Audit logging failed: $e');
    }
  }
}
