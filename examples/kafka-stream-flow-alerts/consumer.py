from confluent_kafka import Consumer, KafkaError
import sys
import os
from google.protobuf import json_format
from google.protobuf.message import DecodeError

# Import generated protobuf modules for client usage
try:
    from protos_gen.client import (
        option_state_client_pb2,
        trade_report_client_pb2,
        options_client_pb2,
        flow_alert_client_pb2,
    )
except ImportError as e:
    print("Error: Protobuf module not found. The 'protos_gen/client' directory should contain:")
    print("  - option_state_client_pb2.py")
    print("  - trade_report_client_pb2.py")
    print("  - options_client_pb2.py")
    print("  - flow_alert_client_pb2.py")
    print(f"\nImport error: {e}")
    sys.exit(1)


def filter_fields(topic: str, decoded_message: dict) -> dict:
    return decoded_message


# Topic to protobuf message mapping
TOPIC_PROTO_MAP = {
    'option-states': option_state_client_pb2.OptionState,
    'all-trade-report': trade_report_client_pb2.TradeReport,
    'all-option-trades': options_client_pb2.OptionTrade,
    'flow-alerts': flow_alert_client_pb2.FlowAlert,
}


def decode_protobuf_message(topic: str, payload: bytes):
    """
    Decode a protobuf message based on the topic and apply field filtering.
    
    Args:
        topic: The Kafka topic name
        payload: The message payload bytes
        
    Returns:
        Decoded and filtered protobuf message as dict, or None if decoding fails
    """
    proto_class = TOPIC_PROTO_MAP.get(topic)
    if not proto_class:
        return None
    
    try:
        message = proto_class()
        message.ParseFromString(payload)
        decoded = json_format.MessageToDict(message, preserving_proto_field_name=True)
        return filter_fields(topic, decoded)
    except DecodeError as e:
        print(f"Failed to decode protobuf: {e}")
        return None


def create_consumer(
    bootstrap_servers: str,
    topic: str,
    group_id: str,
    username: str,
    password: str
):
    """
    Create a Kafka consumer with SASL_SSL authentication.
    
    Args:
        bootstrap_servers: Kafka bootstrap server (e.g., stream.unusualwhales.com:9095)
        topic: Topic name to consume from
        group_id: Consumer group ID
        username: SASL username
        password: SASL password
    """
    
    conf = {
        'bootstrap.servers': bootstrap_servers,
        'group.id': group_id,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,  
        # Security
        'security.protocol': 'SASL_SSL',
        'sasl.mechanism': 'SCRAM-SHA-512',
        'sasl.username': username,
        'sasl.password': password,
        'enable.ssl.certificate.verification': True,
    }
    
    consumer = Consumer(conf)
    consumer.subscribe([topic])
    
    return consumer


def main():
    # Configuration
    BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP', 'stream.unusualwhales.com:9095')
    TOPIC = os.getenv('KAFKA_TOPIC', 'your-topic-name')
    GROUP_ID = os.getenv('KAFKA_GROUP_ID', f'python-consumer-{os.getpid()}')  # Unique group per process
    USERNAME = os.getenv('KAFKA_USERNAME', 'your-username')
    PASSWORD = os.getenv('KAFKA_PASSWORD', 'your-password')
    
    print(f"Connecting to {BOOTSTRAP_SERVERS} (topic: {TOPIC})")
    
    try:
        consumer = create_consumer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            topic=TOPIC,
            group_id=GROUP_ID,
            username=USERNAME,
            password=PASSWORD
        )
        
        print("\nStarting to consume messages... (Ctrl+C to stop)")
        
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"Reached end of partition {msg.partition()}")
                else:
                    print(f"Error: {msg.error()}")
                continue
        
            # Try to decode key as UTF-8, fallback to hex
            if msg.key():
                try:
                    key = msg.key().decode('utf-8')
                except UnicodeDecodeError:
                    key = f"<binary: {msg.key().hex()[:50]}...>"
            else:
                key = None
            print(f"Key: {key}")
            
            # Try to decode as protobuf first
            decoded = decode_protobuf_message(msg.topic(), msg.value())
            if decoded:
                import json
                print(f"Decoded Message:")
                print(json.dumps(decoded, indent=2))
            else:
                # Fallback to raw bytes display
                try:
                    value = msg.value().decode('utf-8')
                except UnicodeDecodeError:
                    value = f"<binary: {len(msg.value())} bytes, hex: {msg.value().hex()[:50]}...>"
                print(f"Value: {value}")
            print(f"------------------------")
            
    except KeyboardInterrupt:
        print("\nShutting down consumer...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        consumer.close()
        print("Consumer closed.")


if __name__ == '__main__':
    main()
