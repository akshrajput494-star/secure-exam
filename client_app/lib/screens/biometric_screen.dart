import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/exam_model.dart';
import '../services/biometric_service.dart';
import 'exam_view_screen.dart';

class BiometricScreen extends StatefulWidget {
  final ExamModel exam;
  
  const BiometricScreen({super.key, required this.exam});

  @override
  State<BiometricScreen> createState() => _BiometricScreenState();
}

class _BiometricScreenState extends State<BiometricScreen> with SingleTickerProviderStateMixin {
  int _attempts = 0;
  bool _isLockedOut = false;
  late AnimationController _animController;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _animController.dispose();
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _authenticate() async {
    if (_isLockedOut) return;

    final biometricService = Provider.of<BiometricService>(context, listen: false);
    final isAvailable = await biometricService.checkBiometricAvailability();
    
    if (!isAvailable) {
      _showError('Strong biometric authentication is required on this device.');
      return;
    }

    final success = await biometricService.authenticate(
      'Verify identity to unlock ${widget.exam.title}',
    );

    if (success) {
      if (!mounted) return;
      // Navigate to View Screen
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (context) => ExamViewScreen(exam: widget.exam),
        ),
      );
    } else {
      setState(() {
        _attempts++;
        if (_attempts >= 5) {
          _isLockedOut = true;
          _showError('Maximum attempts reached. Locked out.');
        } else {
          _showError('Verification failed. Attempt $_attempts of 5.');
        }
      });
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  String _formatCountdown(DateTime target) {
    final diff = target.difference(DateTime.now());
    if (diff.isNegative) return 'Exam Started';
    final minutes = diff.inMinutes.remainder(60);
    final seconds = diff.inSeconds.remainder(60);
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Superintendent Verification')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Unlock: ${widget.exam.title}',
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Text(
                _formatCountdown(widget.exam.scheduledStart),
                style: const TextStyle(fontSize: 32, fontFamily: 'monospace'),
              ),
              const SizedBox(height: 48),
              ScaleTransition(
                scale: Tween<double>(begin: 0.9, end: 1.1).animate(
                  CurvedAnimation(parent: _animController, curve: Curves.easeInOut),
                ),
                child: Icon(
                  Icons.fingerprint,
                  size: 120,
                  color: _isLockedOut ? Colors.red : Theme.of(context).colorScheme.primary,
                ),
              ),
              const SizedBox(height: 48),
              const Text(
                'Superintendent verification is required to decrypt the exam materials.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _isLockedOut ? null : _authenticate,
                onIcon: const Icon(Icons.lock_open),
                label: const Text('Verify Identity'),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
