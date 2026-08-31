import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/exam_model.dart';
import '../services/api_service.dart';
import '../services/kafka_service.dart';
import 'biometric_screen.dart';

class ExamListScreen extends StatefulWidget {
  const ExamListScreen({super.key});

  @override
  State<ExamListScreen> createState() => _ExamListScreenState();
}

class _ExamListScreenState extends State<ExamListScreen> {
  List<ExamModel> _exams = [];
  bool _isLoading = true;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _loadExams();
    _setupKafka();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _setupKafka() {
    final kafka = Provider.of<KafkaService>(context, listen: false);
    // Dummy token for demonstration
    kafka.connect('dummy_socket_token');
    kafka.onKeyReceived = (examId, dekBase64) {
      // In reality, you'd store the key and update the exam status
      if (mounted) {
        setState(() {
          final index = _exams.indexWhere((e) => e.id == examId);
          if (index != -1) {
            _exams[index].status = ExamStatus.keysReceived;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Key received for exam ${_exams[index].title}')),
            );
          }
        });
      }
    };
  }

  Future<void> _loadExams() async {
    setState(() => _isLoading = true);
    try {
      final apiService = Provider.of<ApiService>(context, listen: false);
      // Dummy data fallback if server isn't running
      try {
        _exams = await apiService.fetchExams();
      } catch (e) {
        _exams = [
          ExamModel(
            id: 'exam_1',
            title: 'Mathematics Final',
            subject: 'MATH101',
            scheduledStart: DateTime.now().add(const Duration(minutes: 30)),
            durationMinutes: 120,
            blobSha256: 'abc123hash',
            status: ExamStatus.downloaded,
          ),
          ExamModel(
            id: 'exam_2',
            title: 'Physics Midterm',
            subject: 'PHYS201',
            scheduledStart: DateTime.now().add(const Duration(hours: 2)),
            durationMinutes: 90,
            blobSha256: 'def456hash',
            status: ExamStatus.pending,
          )
        ];
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  String _formatCountdown(DateTime target) {
    final diff = target.difference(DateTime.now());
    if (diff.isNegative) return 'Started';
    final hours = diff.inHours;
    final minutes = diff.inMinutes.remainder(60);
    final seconds = diff.inSeconds.remainder(60);
    return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  Widget _buildStatusChip(ExamStatus status) {
    Color color;
    String label;
    switch (status) {
      case ExamStatus.pending:
        color = Colors.grey;
        label = 'Pending Download';
        break;
      case ExamStatus.downloaded:
        color = Colors.blue;
        label = 'Downloaded';
        break;
      case ExamStatus.keysReceived:
        color = Colors.orange;
        label = 'Keys Received';
        break;
      case ExamStatus.decrypted:
        color = Colors.green;
        label = 'Decrypted';
        break;
    }
    return Chip(
      label: Text(label, style: const TextStyle(color: Colors.white, fontSize: 12)),
      backgroundColor: color,
    );
  }

  @override
  Widget build(BuildContext context) {
    final kafka = Provider.of<KafkaService>(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Assigned Exams'),
        actions: [
          Icon(
            kafka.isConnected ? Icons.cloud_done : Icons.cloud_off,
            color: kafka.isConnected ? Colors.green : Colors.red,
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadExams,
              child: ListView.builder(
                itemCount: _exams.length,
                padding: const EdgeInsets.all(16),
                itemBuilder: (context, index) {
                  final exam = _exams[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 16),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text(
                                  exam.title,
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                              ),
                              _buildStatusChip(exam.status),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text('Subject: ${exam.subject}'),
                          Text('Duration: ${exam.durationMinutes} mins'),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Starts In:', style: TextStyle(fontWeight: FontWeight.bold)),
                                  Text(
                                    _formatCountdown(exam.scheduledStart),
                                    style: const TextStyle(
                                      fontSize: 24,
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ],
                              ),
                              if (exam.status == ExamStatus.pending)
                                ElevatedButton.icon(
                                  onIcon: const Icon(Icons.download),
                                  label: const Text('Download'),
                                  onPressed: () {
                                    setState(() {
                                      exam.status = ExamStatus.downloaded;
                                    });
                                  },
                                )
                              else if (exam.status == ExamStatus.keysReceived)
                                FilledButton.icon(
                                  onIcon: const Icon(Icons.lock_open),
                                  label: const Text('Unlock'),
                                  style: FilledButton.styleFrom(backgroundColor: Colors.orange),
                                  onPressed: () {
                                    Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (context) => BiometricScreen(exam: exam),
                                      ),
                                    );
                                  },
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }
}
