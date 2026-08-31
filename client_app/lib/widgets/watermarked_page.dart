import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class WatermarkedPage extends StatelessWidget {
  final Widget content;
  final String centerCode;

  const WatermarkedPage({
    super.key,
    required this.content,
    required this.centerCode,
  });

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final watermarkText = '$centerCode - ${DateFormat('yyyy-MM-dd').format(now)}';
    
    return Stack(
      children: [
        // Base Content
        Container(
          color: Colors.white,
          child: content,
        ),
        
        // Diagonal Watermark overlay (non-interactive)
        IgnorePointer(
          child: Center(
            child: Transform.rotate(
              angle: -0.785398, // -45 degrees
              child: Opacity(
                opacity: 0.1, // Very subtle, but visible
                child: Text(
                  watermarkText,
                  style: const TextStyle(
                    fontSize: 48,
                    fontWeight: FontWeight.bold,
                    color: Colors.black,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          ),
        ),
        
        // Footer timestamp and trace info
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: IgnorePointer(
            child: Container(
              padding: const EdgeInsets.all(4),
              color: Colors.black.withOpacity(0.8),
              child: Text(
                'CENTER: $centerCode | VIEWED: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(now)} | DEVICE: SecureApp-v1.0',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontFamily: 'monospace',
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
