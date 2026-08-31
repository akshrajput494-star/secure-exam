import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json

from cloud_functions.key_broadcaster.main import handler

class TestBroadcaster(unittest.TestCase):
    @patch('cloud_functions.key_broadcaster.main.get_db_connection')
    @patch('cloud_functions.key_broadcaster.main.get_kms_client')
    @patch('cloud_functions.key_broadcaster.main.get_kafka_producer')
    @patch.dict('os.environ', {'KMS_KEY_ID': 'test-kms-key', 'AWS_REGION': 'ap-south-1'})
    def test_exams_within_t15_are_selected(self, mock_kafka, mock_kms, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simulate one valid exam
        mock_cursor.fetchall.side_effect = [
            [{'id': '123e4567-e89b-12d3-a456-426614174000', 'scheduled_start': datetime.now(), 'wrapped_dek': b'wrapped'}],
            [{'center_id': 'center-1'}]
        ]
        # Simulate no existing key_broadcast record
        mock_cursor.fetchone.return_value = None
        
        mock_kms_instance = MagicMock()
        mock_kms.return_value = mock_kms_instance
        mock_kms_instance.decrypt.return_value = {'Plaintext': b'plaintext_dek'}
        
        mock_kafka_instance = MagicMock()
        mock_kafka.return_value = mock_kafka_instance
        
        result = handler({}, {})
        
        self.assertEqual(result['statusCode'], 200)
        mock_kms_instance.decrypt.assert_called_once_with(CiphertextBlob=b'wrapped', KeyId='test-kms-key')
        mock_kafka_instance.produce.assert_called_once()
        
        # Check audit log insert
        execute_calls = mock_cursor.execute.call_args_list
        audit_call_found = False
        for call in execute_calls:
            query = call[0][0]
            if 'INSERT INTO audit_log' in query:
                audit_call_found = True
                break
        self.assertTrue(audit_call_found)
        mock_conn.commit.assert_called_once()

    @patch('cloud_functions.key_broadcaster.main.get_db_connection')
    @patch.dict('os.environ', {'KMS_KEY_ID': 'test-kms-key'})
    def test_no_exams_skipped(self, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        result = handler({}, {})
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(result['body'], 'No action needed')

    @patch('cloud_functions.key_broadcaster.main.get_db_connection')
    @patch('cloud_functions.key_broadcaster.main.get_kms_client')
    @patch('cloud_functions.key_broadcaster.main.get_kafka_producer')
    @patch.dict('os.environ', {'KMS_KEY_ID': 'test-kms-key'})
    def test_idempotency_skip(self, mock_kafka, mock_kms, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.side_effect = [
            [{'id': '123e4567-e89b-12d3-a456-426614174000', 'scheduled_start': datetime.now(), 'wrapped_dek': b'wrapped'}],
        ]
        # Simulate existing record
        mock_cursor.fetchone.return_value = {'id': 'existing'}
        
        result = handler({}, {})
        self.assertEqual(result['statusCode'], 200)
        mock_kms.assert_not_called()

    @patch('cloud_functions.key_broadcaster.main.get_db_connection')
    @patch('cloud_functions.key_broadcaster.main.get_kms_client')
    @patch('cloud_functions.key_broadcaster.main.get_kafka_producer')
    @patch.dict('os.environ', {'KMS_KEY_ID': 'test-kms-key'})
    def test_partial_failure(self, mock_kafka, mock_kms, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.side_effect = [
            [
                {'id': 'exam1', 'scheduled_start': datetime.now(), 'wrapped_dek': b'wrapped1'},
                {'id': 'exam2', 'scheduled_start': datetime.now(), 'wrapped_dek': b'wrapped2'}
            ],
            [{'center_id': 'center-2'}] # for exam2
        ]
        
        # Exam 1 fails, Exam 2 succeeds
        def fetchone_side_effect():
            yield None
            yield None
        
        mock_cursor.fetchone.side_effect = [None, None]
        
        mock_kms_instance = MagicMock()
        mock_kms.return_value = mock_kms_instance
        # Fail on first decrypt, succeed on second
        mock_kms_instance.decrypt.side_effect = [Exception("KMS error"), {'Plaintext': b'plaintext_dek2'}]
        
        mock_kafka_instance = MagicMock()
        mock_kafka.return_value = mock_kafka_instance
        
        result = handler({}, {})
        self.assertEqual(result['statusCode'], 200)
        # Verify rollback was called for the first error
        mock_conn.rollback.assert_called_once()
        # Verify commit was called for the second success
        mock_conn.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
