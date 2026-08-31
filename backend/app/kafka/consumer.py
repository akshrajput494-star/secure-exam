import json
import logging
from typing import Any, Dict, List
from confluent_kafka import Consumer, KafkaError, Message
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections per exam center."""
    
    def __init__(self) -> None:
        self._connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, center_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if center_id not in self._connections:
            self._connections[center_id] = []
        self._connections[center_id].append(websocket)
        
    async def disconnect(self, center_id: str, websocket: WebSocket) -> None:
        if center_id in self._connections:
            self._connections[center_id].remove(websocket)
            if not self._connections[center_id]:
                del self._connections[center_id]
                
    async def send_to_center(self, center_id: str, data: Dict[str, Any]) -> int:
        """Send data to all connected clients for a center."""
        count = 0
        if center_id in self._connections:
            for connection in self._connections[center_id]:
                try:
                    await connection.send_json(data)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to send to websocket: {e}")
        return count
        
    async def broadcast_all(self, data: Dict[str, Any]) -> int:
        """Broadcast to all connected centers."""
        count = 0
        for center_id in list(self._connections.keys()):
            count += await self.send_to_center(center_id, data)
        return count


class SecureExamConsumer:
    """Kafka consumer that bridges key broadcasts to WebSocket clients.
    
    Each exam center connects via WebSocket. When a key is broadcast
    on the exam.keys topic, it's relayed to the appropriate center's
    WebSocket connection.
    """
    
    def __init__(self, bootstrap_servers: str, group_id: str, topics: List[str]) -> None:
        conf = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False
        }
        self.consumer = Consumer(conf)
        self.consumer.subscribe(topics)
        self.running = False
        
    async def start_consuming(self, websocket_manager: WebSocketManager) -> None:
        """Start consuming in a background task."""
        self.running = True
        try:
            while self.running:
                # Use small timeout for non-blocking poll in async context
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break
                
                if msg.topic() == 'exam.keys':
                    await self._process_key_message(msg, websocket_manager)
                    
        finally:
            self.close()
            
    async def _process_key_message(self, msg: Message, websocket_manager: WebSocketManager) -> None:
        """Process a key broadcast message and relay to WebSocket."""
        try:
            value = msg.value()
            if not value:
                return
            data = json.loads(value.decode('utf-8'))
            target_centers = data.get("target_centers", [])
            
            # Relay to each target center
            for center_id in target_centers:
                await websocket_manager.send_to_center(center_id, data)
                
            self.commit(msg)
        except Exception as e:
            logger.error(f"Error processing key message: {e}")
            
    def commit(self, msg: Message) -> None:
        """Manually commit offset after confirmed client receipt."""
        self.consumer.commit(message=msg)
        
    def close(self) -> None:
        """Gracefully shut down the consumer."""
        self.running = False
        self.consumer.close()
