import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/exam_model.dart';
import '../services/watermark_service.dart';
import '../services/api_service.dart';
import '../widgets/watermarked_page.dart';
import '../services/print_service.dart';
import '../services/offline_cache_service.dart';
import 'package:flutter/services.dart';

class ExamViewScreen extends StatefulWidget {
  final ExamModel exam;
  const ExamViewScreen({super.key, required this.exam});

  @override
  State<ExamViewScreen> createState() => _ExamViewScreenState();
}

class _ExamViewScreenState extends State<ExamViewScreen> {
  static const _platform = MethodChannel('com.secure_exam.client/secure');
  bool _isPrinting = false;
  
  // Dummy pages for demonstration instead of actual PDF rendering
  final List<String> _pages = [
    'Page 1: Instructions\n\n1. Do not open until instructed.\n2. Use black pen only.',
    'Page 2: Question 1\n\nCalculate the mass of the sun given...',
    'Page 3: Question 2\n\nDescribe the principles of thermodynamics...',
  ];

  @override
  void initState() {
    super.initState();
    _secureScreen();
    _logAudit('exam_viewed');
  }

  Future<void> _secureScreen() async {
    try {
      // In a real Android app, this calls getWindow().setFlags(FLAG_SECURE, FLAG_SECURE)
      // await _platform.invokeMethod('setSecureFlag');
    } catch (e) {
      print('Failed to secure screen: $e');
    }
  }
  
  Future<void> _unsecureScreen() async {
    try {
      // await _platform.invokeMethod('clearSecureFlag');
    } catch (e) {
      print('Failed to unsecure screen: $e');
    }
  }

  @override
  void dispose() {
    _unsecureScreen();
    super.dispose();
  }

  Future<void> _logAudit(String action, {Map<String, dynamic>? extra}) async {
    try {
      final apiService = Provider.of<ApiService>(context, listen: false);
      await apiService.reportAuditEvent(action, {
        'examId': widget.exam.id,
        if (extra != null) ...extra,
      });
    } catch (e) {
      print('Audit fail: $e');
    }
  }

  Future<void> _handlePrint() async {
    setState(() => _isPrinting = true);
    try {
      final printService = Provider.of<PrintService>(context, listen: false);
      
      // Show printer selection dialog
      final selectedPrinter = await printService.showPrinterSelectionDialog(context);
      
      // Print with watermarking (null printer = system dialog)
      final record = await printService.printExam(
        decryptedPdfBytes: Uint8List(0), // Would be real decrypted PDF
        examId: widget.exam.id,
        examTitle: widget.exam.title,
        centerCode: 'CTR-9921',
        superintendentName: 'SUP-JOHN-DOE',
        targetPrinter: selectedPrinter,
      );
      
      _logAudit('exam_printed', extra: record.toJson());
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Print job ${record.printJobId.substring(0, 8)} submitted.'),
            backgroundColor: record.status == PrintJobStatus.completed 
                ? Colors.green : Colors.orange,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Print failed: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isPrinting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () async => false, // Prevent back button navigation easily
      child: Scaffold(
        appBar: AppBar(
          title: Text(widget.exam.title),
          automaticallyImplyLeading: false, // Hide back button
          actions: [
            IconButton(
              icon: _isPrinting 
                  ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Icon(Icons.print),
              onPressed: _isPrinting ? null : _handlePrint,
              tooltip: 'Secure Print',
            ),
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () {
                _logAudit('exam_closed');
                Navigator.of(context).pop(); // Can explicitly close
              },
            ),
          ],
        ),
        body: PageView.builder(
          itemCount: _pages.length,
          itemBuilder: (context, index) {
            return WatermarkedPage(
              centerCode: 'CTR-9921',
              content: Center(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Text(
                    _pages[index],
                    style: const TextStyle(fontSize: 18),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
