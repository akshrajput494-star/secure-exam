class AppConfig {
  static const bool isDevelopment = bool.fromEnvironment('dart.vm.product') == false;
  
  static const String apiBaseUrl = isDevelopment 
      ? 'http://10.0.2.2:8000/api/v1' 
      : 'https://api.secure-exam.example.com/api/v1';
      
  static const String webSocketUrl = isDevelopment 
      ? 'ws://10.0.2.2:8000/ws/exam-keys' 
      : 'wss://api.secure-exam.example.com/ws/exam-keys';
      
  static const Duration apiTimeout = Duration(seconds: 30);
  static const Duration wsPingInterval = Duration(seconds: 30);
}
