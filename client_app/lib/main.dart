import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/login_screen.dart';
import 'screens/exam_list_screen.dart';
import 'services/api_service.dart';
import 'services/kafka_service.dart';
import 'services/crypto_service.dart';
import 'services/biometric_service.dart';
import 'services/watermark_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    MultiProvider(
      providers: [
        Provider<ApiService>(create: (_) => ApiService()),
        Provider<KafkaService>(create: (_) => KafkaService()),
        Provider<CryptoService>(create: (_) => CryptoService()),
        Provider<BiometricService>(create: (_) => BiometricService()),
        Provider<WatermarkService>(create: (_) => WatermarkService()),
      ],
      child: const SecureExamApp(),
    ),
  );
}

class SecureExamApp extends StatelessWidget {
  const SecureExamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Secure Exam Client',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue.shade800,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue.shade800,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      initialRoute: '/login',
      routes: {
        '/login': (context) => const LoginScreen(),
        '/exams': (context) => const ExamListScreen(),
        // Biometric and View screens will be pushed dynamically with arguments
      },
      builder: (context, child) {
        // Global error handling overlay could be added here
        return child!;
      },
    );
  }
}
