import 'package:local_auth/local_auth.dart';
import 'package:local_auth_android/local_auth_android.dart';
// Note: iOS support not required per requirements, focusing on Android

class BiometricService {
  final LocalAuthentication _auth = LocalAuthentication();

  Future<bool> checkBiometricAvailability() async {
    final isAvailable = await _auth.canCheckBiometrics;
    final isDeviceSupported = await _auth.isDeviceSupported();
    return isAvailable && isDeviceSupported;
  }

  // Ensures ISO/IEC 19794 compliance indirectly by requiring strong biometrics
  // No PIN/Pattern fallback allowed
  Future<bool> authenticate(String reason) async {
    try {
      final authenticated = await _auth.authenticate(
        localizedReason: reason,
        authMessages: const [
          AndroidAuthMessages(
            signInTitle: 'Superintendent Verification Required',
            cancelButton: 'Cancel',
          ),
        ],
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: true, // Crucial for security, disables PIN/pattern
          useErrorDialogs: true,
        ),
      );
      return authenticated;
    } catch (e) {
      print('Biometric auth error: $e');
      return false;
    }
  }
  
  // Dummy challenge token generation - in real app, involves signing a server challenge
  String generateSignedChallengeToken() {
    return "signed_token_${DateTime.now().millisecondsSinceEpoch}";
  }
}
