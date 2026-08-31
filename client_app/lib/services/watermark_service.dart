import 'dart:typed_data';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';

class WatermarkService {
  Future<Uint8List> generateWatermarkedPdf(
      Uint8List originalPdfBytes, String centerCode, String superintendentName) async {
    
    final pdf = pw.Document();
    final originalDoc = await PdfDocument.load(originalPdfBytes);
    final uuid = const Uuid().v4().substring(0, 8); // Short UUID for tracking

    for (var i = 0; i < originalDoc.pages.count; i++) {
      final pageInfo = originalDoc.pages[i];
      final pdfPage = originalDoc.pages[i]; // Need to extract graphics properly in real app
      
      // Due to the pdf package limitations, completely overlaying a parsed PDF is complex
      // This is a simplified representation of the watermarking logic
      pdf.addPage(
        pw.Page(
          pageFormat: PdfPageFormat.a4,
          build: (pw.Context context) {
            return pw.Stack(
              children: [
                // Original PDF page content would go here
                pw.Center(
                  child: pw.Text('ORIGINAL CONTENT PLACEHOLDER'),
                ),
                
                // Diagonal Watermark
                pw.Positioned(
                  child: pw.Transform.rotateBox(
                    angle: -0.785398, // -45 degrees in radians
                    child: pw.Opacity(
                      opacity: 0.3,
                      child: pw.Text(
                        '$centerCode - ${DateFormat('yyyy-MM-dd').format(DateTime.now())}',
                        style: pw.TextStyle(
                          fontSize: 60,
                          color: PdfColors.grey,
                          fontWeight: pw.FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ),
                
                // Footer
                pw.Positioned(
                  bottom: 10,
                  left: 0,
                  right: 0,
                  child: pw.Container(
                    color: PdfColors.black,
                    padding: const pw.EdgeInsets.all(4),
                    child: pw.Text(
                      'CENTER: $centerCode | DATE: ${DateFormat('yyyy-MM-dd').format(DateTime.now())} | TIME: ${DateFormat('HH:mm:ss').format(DateTime.now())} | COPY: $uuid | SUP: $superintendentName',
                      style: pw.TextStyle(
                        color: PdfColors.white,
                        fontSize: 10,
                        font: pw.Font.courier(),
                      ),
                      textAlign: pw.TextAlign.center,
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      );
    }
    return pdf.save();
  }

  Future<void> printWatermarkedExam(Uint8List watermarkedPdf, String jobName) async {
    await Printing.layoutPdf(
      onLayout: (PdfPageFormat format) async => watermarkedPdf,
      name: jobName,
    );
  }
}
