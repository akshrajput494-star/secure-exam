import json
import logging
from typing import Any, Dict, List
from confluent_kafka import Producer

logger = logging.getLogger(__name__)

class SecureExamProducer:
    """Kafka producer for Secure Exam event publishing.
    
    Topics:
    - exam.lifecycle: Exam status change events
    - exam.keys: Decryption key broadcasts (high-security)
    - exam.audit: Audit log events for async processing
    """
    
    def __init__(self, bootstrap_servers: str, security_protocol: str = 'PLAINTEXT') -> None:
        conf = {
            'bootstrap.servers': bootstrap_servers,
            'security.protocol': security_protocol,
            'acks': 'all',
            'enable.idempotence': True,
            'max.in.flight.requests.per.connection': 5,
            'compression.type': 'lz4'
        }
        self.producer = Producer(conf)

    async def publish_exam_event(self, event_type: str, exam_id: str, data: Dict[str, Any]) -> None:
        """Publish an exam lifecycle event."""
        payload = {
            "event_type": event_type,
            "exam_id": exam_id,
            "data": data
        }
        self.producer.produce(
            topic='exam.lifecycle',
            key=exam_id.encode('utf-8'),
            value=json.dumps(payload).encode('utf-8'),
            callback=self._delivery_callback
        )
        self.producer.poll(0)

    async def broadcast_decryption_key(self, exam_id: str, dek: bytes, target_centers: List[str]) -> Dict[str, Any]:
        """Broadcast a DEK to specific exam centers.
        Returns delivery metadata (topic, partition, offset).
        """
        # Note: In production, the `dek` broadcasted here is usually the wrapped DEK
        payload = {
            "exam_id": exam_id,
            "encrypted_dek": dek.hex(),
            "target_centers": target_centers
        }
        
        self.producer.produce(
            topic='exam.keys',
            key=exam_id.encode('utf-8'),
            value=json.dumps(payload).encode('utf-8'),
            callback=self._delivery_callback
        )
        self.producer.poll(0)
        return {"status": "broadcast_initiated", "exam_id": exam_id}

    async def publish_audit_event(self, action: str, metadata: Dict[str, Any]) -> None:
        """Publish an audit event for async processing."""
        payload = {
            "action": action,
            "metadata": metadata
        }
        self.producer.produce(
            topic='exam.audit',
            value=json.dumps(payload).encode('utf-8'),
            callback=self._delivery_callback
        )
        self.producer.poll(0)

    def _delivery_callback(self, err: Any, msg: Any) -> None:
        """Callback for delivery reports."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def flush(self, timeout: float = 10.0) -> None:
        """Flush pending messages."""
        self.producer.flush(timeout)

    def close(self) -> None:
        """Gracefully shut down the producer."""
        self.flush()
