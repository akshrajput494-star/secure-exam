import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/app_config.dart';

/// Callback when a decryption key is received from the T-15 broadcast.
typedef KeyReceivedCallback = void Function(String examId, String dekBase64);

/// WebSocket connection states.
enum KafkaConnectionState { disconnected, connecting, connected, reconnecting }

/// Kafka key distribution service via WebSocket bridge.
///
/// Connects to the backend's WebSocket endpoint which bridges Kafka's
/// `exam.keys` topic. Implements strict T-minus 15 key synchronization:
///
/// 1. Client connects and authenticates via JWT
/// 2. WebSocket stays open, heartbeat keeps connection alive
/// 3. At T-15, backend's Lambda broadcasts DEK to Kafka
/// 4. Backend consumer relays DEK to this client via WebSocket
/// 5. Client stores DEK in Android Keystore for offline decryption
///
/// Features exponential backoff reconnection to handle network
/// instability at exam centers.
class KafkaService {
  WebSocketChannel? _channel;
  Timer? _pingTimer;
  Timer? _reconnectTimer;
  KeyReceivedCallback? onKeyReceived;
  KafkaConnectionState connectionState = KafkaConnectionState.disconnected;

  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 10;
  static const Duration _maxBackoff = Duration(seconds: 30);
  String? _currentToken;

  /// Set of exam IDs for which keys have been received.
  final Set<String> receivedKeys = {};

  bool get isConnected => connectionState == KafkaConnectionState.connected;

  /// Connect to the Kafka WebSocket bridge.
  ///
  /// The [token] is a JWT used to authenticate the center's connection.
  /// The backend filters messages to only send keys for exams assigned
  /// to this center.
  void connect(String token) {
    _currentToken = token;
    connectionState = KafkaConnectionState.connecting;

    try {
      final uri = Uri.parse('${AppConfig.webSocketUrl}?token=$token');
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen(
        _handleMessage,
        onDone: () => _handleDisconnect('Connection closed'),
        onError: (error) => _handleDisconnect('Error: $error'),
      );

      connectionState = KafkaConnectionState.connected;
      _reconnectAttempts = 0; // Reset on successful connection
      _startPing();
    } catch (e) {
      connectionState = KafkaConnectionState.disconnected;
      _scheduleReconnect();
    }
  }

  void _handleMessage(dynamic rawMessage) {
    try {
      final data = jsonDecode(rawMessage as String);
      final type = data['type'] as String?;

      switch (type) {
        case 'EXAM_KEY_RELEASE':
          // T-15 key broadcast received
          final examId = data['examId'] as String;
          final dekBase64 = data['dekBase64'] as String;
          receivedKeys.add(examId);
          onKeyReceived?.call(examId, dekBase64);
          break;

        case 'PONG':
          // Heartbeat response — connection is alive
          break;

        case 'KEY_SYNC_STATUS':
          // Server confirms which keys have been broadcast
          final syncedExams = (data['exams'] as List?)?.cast<String>() ?? [];
          receivedKeys.addAll(syncedExams);
          break;

        default:
          // Unknown message type — log but don't crash
          break;
      }
    } catch (e) {
      // Malformed message — ignore
    }
  }

  void _startPing() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(AppConfig.wsPingInterval, (timer) {
      if (isConnected && _channel != null) {
        try {
          _channel!.sink.add(jsonEncode({'type': 'PING'}));
        } catch (_) {
          _handleDisconnect('Ping failed');
        }
      }
    });
  }

  void _handleDisconnect(String reason) {
    _pingTimer?.cancel();
    if (connectionState != KafkaConnectionState.disconnected) {
      connectionState = KafkaConnectionState.reconnecting;
      _scheduleReconnect();
    }
  }

  /// Schedule reconnection with exponential backoff.
  ///
  /// Backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped).
  /// Gives up after [_maxReconnectAttempts] to prevent battery drain.
  void _scheduleReconnect() {
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      connectionState = KafkaConnectionState.disconnected;
      return;
    }

    _reconnectTimer?.cancel();
    final delay = Duration(
      milliseconds: min(
        _maxBackoff.inMilliseconds,
        (pow(2, _reconnectAttempts) * 1000).toInt(),
      ),
    );

    _reconnectAttempts++;
    connectionState = KafkaConnectionState.reconnecting;

    _reconnectTimer = Timer(delay, () {
      if (_currentToken != null) {
        connect(_currentToken!);
      }
    });
  }

  /// Check if a key has been received for a specific exam.
  bool hasKeyForExam(String examId) => receivedKeys.contains(examId);

  /// Reset reconnection counter (e.g., after manual retry).
  void resetReconnect() {
    _reconnectAttempts = 0;
  }

  /// Disconnect and clean up.
  void disconnect() {
    _pingTimer?.cancel();
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    connectionState = KafkaConnectionState.disconnected;
    _currentToken = null;
  }
}
