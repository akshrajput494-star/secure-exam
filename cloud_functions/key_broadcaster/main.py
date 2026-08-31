import os
import json
import logging
import psycopg2
import psycopg2.extras
import boto3
from confluent_kafka import Producer
from datetime import datetime, timezone
import uuid

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_db_connection():
    """Establish and return a synchronous PostgreSQL connection."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    return psycopg2.connect(db_url)

def get_kms_client():
    """Return a boto3 KMS client."""
    region = os.environ.get('AWS_REGION', 'ap-south-1')
    return boto3.client('kms', region_name=region)

def get_kafka_producer():
    """Initialize and return a Kafka producer."""
    bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS')
    if not bootstrap_servers:
        raise ValueError("KAFKA_BOOTSTRAP_SERVERS environment variable is required")
    conf = {
        'bootstrap.servers': bootstrap_servers,
        'client.id': 'key-broadcaster-lambda'
    }
    return Producer(conf)

def delivery_report(err, msg):
    """Callback for Kafka producer delivery."""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def handler(event, context):
    """
    AWS Lambda entry point.
    Queries the database for exams starting within 15 minutes that haven't had keys broadcast.
    Unwraps DEK and publishes to Kafka.
    """
    logger.info("Starting key broadcast check")
    
    kms_key_id = os.environ.get('KMS_KEY_ID')
    if not kms_key_id:
        logger.error("KMS_KEY_ID not set")
        return {"statusCode": 500, "body": "Configuration error"}

    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Query for qualifying exams
        query = """
            SELECT id, scheduled_start, wrapped_dek 
            FROM exams 
            WHERE (scheduled_start - NOW()) <= interval '15 minutes' 
              AND status != 'KEYS_BROADCAST'
            FOR UPDATE SKIP LOCKED;
        """
        cursor.execute(query)
        exams = cursor.fetchall()
        
        if not exams:
            logger.info("No exams pending key broadcast.")
            return {"statusCode": 200, "body": "No action needed"}
        
        logger.info(f"Found {len(exams)} exams requiring key broadcast.")
        
        kms_client = get_kms_client()
        kafka_producer = get_kafka_producer()
        
        for exam in exams:
            exam_id = str(exam['id'])
            wrapped_dek = exam['wrapped_dek']
            
            try:
                # Check for idempotency
                cursor.execute("SELECT id FROM key_broadcasts WHERE exam_id = %s", (exam_id,))
                if cursor.fetchone():
                    logger.warning(f"Exam {exam_id} already has a key_broadcasts record. Skipping.")
                    continue
                
                # Unwrap DEK
                decrypt_response = kms_client.decrypt(
                    CiphertextBlob=bytes(wrapped_dek),
                    KeyId=kms_key_id
                )
                plaintext_dek = decrypt_response['Plaintext']
                
                # Fetch assigned center IDs
                cursor.execute("SELECT center_id FROM exam_center_assignments WHERE exam_id = %s", (exam_id,))
                centers = cursor.fetchall()
                center_ids = [str(c['center_id']) for c in centers]
                
                # Publish to Kafka
                payload = {
                    "exam_id": exam_id,
                    "dek": plaintext_dek.hex(),
                    "centers": center_ids,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                kafka_producer.produce(
                    topic='exam.keys',
                    key=exam_id.encode('utf-8'),
                    value=json.dumps(payload).encode('utf-8'),
                    callback=delivery_report
                )
                kafka_producer.poll(0)
                
                # Update database records
                cursor.execute("UPDATE exams SET status = 'KEYS_BROADCAST' WHERE id = %s", (exam_id,))
                
                cursor.execute("""
                    INSERT INTO key_broadcasts (id, exam_id, broadcast_at, kafka_topic, kafka_partition, kafka_offset, confirmed_receipt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (str(uuid.uuid4()), exam_id, datetime.now(timezone.utc), 'exam.keys', 0, 0, False))
                
                cursor.execute("""
                    INSERT INTO audit_log (exam_id, action, metadata)
                    VALUES (%s, %s, %s)
                """, (exam_id, 'KEY_BROADCAST_SENT', json.dumps({"centers_count": len(center_ids)})))
                
                # Flush Kafka to ensure delivery
                kafka_producer.flush(10)
                
                # Commit transaction per exam to prevent all-or-nothing failures across multiple exams
                conn.commit()
                logger.info(f"Successfully broadcast key for exam {exam_id}")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to process exam {exam_id}: {str(e)}")
                # Continue with other exams
                
    except Exception as e:
        logger.error(f"Database or infrastructure error: {str(e)}")
        return {"statusCode": 500, "body": "Internal server error"}
    finally:
        if conn:
            cursor.close()
            conn.close()
            
    return {"statusCode": 200, "body": "Broadcast completed"}
