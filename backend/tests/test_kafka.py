import pytest
from unittest.mock import MagicMock, patch
from app.services.kafka import KafkaService

@pytest.fixture
def mock_producer():
    with patch('app.services.kafka.Producer') as mock:
        yield mock

def test_producer_initialization(mock_producer):
    service = KafkaService(bootstrap_servers="kafka:9092")
    mock_producer.assert_called_once()

def test_publish_exam_event(mock_producer):
    instance = mock_producer.return_value
    service = KafkaService(bootstrap_servers="localhovers="kafka:9092")
    service.publish_event("exam.events", "exam-123", {"status": "CREATED"})
    
    instance.produce.assert_called_once()
    args, kwargs = instance.produce.call_args
    assert kwargs['topic'] == 'exam.events'
    assert kwargs['key'] == 'exam-123'
    assert b'"status": "CREATED"' in kwargs['value']

def test_broadcast_decryption_key(mock_producer):
    instance = mock_producer.return_value
    service = KafkaService(bootstrap_servers="localhovers="kafka:9092")
    service.broadcast_key("exam-123", b"testdek1234567890123456789012345", ["center-1"])
    
    instance.produce.assert_called_once()
    args, kwargs = instance.produce.call_args
    assert kwargs['topic'] == 'exam.keys'
    assert kwargs['key'] == 'exam-123'

def test_delivery_callback_success():
    service = KafkaService(bootstrap_servers="localhovers="kafka:9092")
    mock_msg = MagicMock()
    mock_msg.topic.return_value = "exam.events"
    mock_msg.partition.return_value = 0
    
    # Should not raise
    service.delivery_report(None, mock_msg)

def test_delivery_callback_error():
    service = KafkaService(bootstrap_servers="kafka:9092")
    mock_msg = MagicMock()
    mock_err = Exception("Kafka connection failed")
    
    # Should log but not raise
    service.delivery_report(mock_err, mock_msg)
    