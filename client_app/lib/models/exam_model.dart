import 'dart:typed_data';

enum ExamStatus { pending, downloaded, keysReceived, decrypted }

class ExamModel {
  final String id;
  final String title;
  final String subject;
  final DateTime scheduledStart;
  final int durationMinutes;
  ExamStatus status;
  final String blobSha256;

  ExamModel({
    required this.id,
    required this.title,
    required this.subject,
    required this.scheduledStart,
    required this.durationMinutes,
    this.status = ExamStatus.pending,
    required this.blobSha256,
  });

  factory ExamModel.fromJson(Map<String, dynamic> json) {
    return ExamModel(
      id: json['id'],
      title: json['title'],
      subject: json['subject'],
      scheduledStart: DateTime.parse(json['scheduledStart']),
      durationMinutes: json['durationMinutes'],
      status: ExamStatus.values.firstWhere(
        (e) => e.toString() == 'ExamStatus.${json['status']}',
        orElse: () => ExamStatus.pending,
      ),
      blobSha256: json['blobSha256'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'subject': subject,
      'scheduledStart': scheduledStart.toIso8601String(),
      'durationMinutes': durationMinutes,
      'status': status.toString().split('.').last,
      'blobSha256': blobSha256,
    };
  }
}

class ExamDownloadModel {
  final String examId;
  final Uint8List encryptedBlob;
  final DateTime downloadedAt;

  ExamDownloadModel({
    required this.examId,
    required this.encryptedBlob,
    required this.downloadedAt,
  });
}

class AuditEntry {
  final String action;
  final DateTime timestamp;
  final Map<String, dynamic> metadata;

  AuditEntry({
    required this.action,
    required this.timestamp,
    required this.metadata,
  });

  Map<String, dynamic> toJson() {
    return {
      'action': action,
      'timestamp': timestamp.toIso8601String(),
      'metadata': metadata,
    };
  }
}
