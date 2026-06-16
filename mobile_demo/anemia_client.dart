import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

/// Production integration client for SwasthAI Anemia Detection API.
class SwasthAIClient {
  final String apiBaseUrl;

  SwasthAIClient({required this.apiBaseUrl});

  /// Send base64-encoded conjunctiva or fingernail image to API for screening.
  Future<Map<String, dynamic>> predictAnemia({
    required File imageFile,
    required String scanType, // 'conjunctiva' or 'fingernail'
    String patientId = 'MOBILE_USER',
  }) async {
    final String url = '$apiBaseUrl/predict/b64';

    try {
      // 1. Read image bytes and convert to Base64
      List<int> imageBytes = await imageFile.readAsBytes();
      String base64Image = base64Encode(imageBytes);

      // 2. Prepare payload
      Map<String, dynamic> payload = {
        'image_b64': base64Image,
        'scan_type': scanType,
        'patient_id': patientId,
      };

      // 3. Send POST request
      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          'success': false,
          'error': 'Server error: ${response.statusCode}',
          'message': response.body,
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Network connection failed',
        'message': e.toString(),
      };
    }
  }

  /// Request a comprehensive health screening report (conjunctiva + fingernail).
  Future<Map<String, dynamic>> generateScreeningReport({
    required File conjunctivaFile,
    required File fingernailFile,
    required String patientName,
    required int patientAge,
    required String patientGender, // 'female' or 'male'
    required List<String> symptoms,
  }) async {
    final String url = '$apiBaseUrl/report';

    try {
      // Convert images to base64
      List<int> conjBytes = await conjunctivaFile.readAsBytes();
      List<int> nailBytes = await fingernailFile.readAsBytes();
      String conjB64 = base64Encode(conjBytes);
      String nailB64 = base64Encode(nailBytes);

      // Prepare payload
      Map<String, dynamic> payload = {
        'conjunctiva_b64': conjB64,
        'fingernail_b64': nailB64,
        'patient_name': patientName,
        'patient_age': patientAge,
        'patient_gender': patientGender,
        'symptoms': symptoms,
      };

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          'success': false,
          'error': 'Server error: ${response.statusCode}',
          'message': response.body,
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Network connection failed',
        'message': e.toString(),
      };
    }
  }
}
