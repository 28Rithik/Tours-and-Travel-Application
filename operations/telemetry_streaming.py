"""
=====================================================================================
SIVA GAYATHRI TOURS & TRAVELS — DECOUPLED TELEMETRY STREAMING PIPELINE (RABBITMQ)
Decouples high-throughput GPS ingestion from database writes & real-time queries.
=====================================================================================
"""
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from operations.spatial_engine import SpatialEngine, get_postgis_connection

logger = logging.getLogger(__name__)

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "travelerp"
RABBITMQ_PASS = "travelerp"
EXCHANGE_NAME = "telemetry.exchange"
QUEUE_NAME = "telemetry.gps.queue"
ROUTING_KEY_PREFIX = "telemetry.gps"

# Stream metrics for Prometheus / Grafana
STREAM_METRICS = {
    "total_messages_published": 0,
    "total_messages_consumed": 0,
    "last_publish_latency_ms": 0.0,
    "broker_status": "disconnected"
}


class TelemetryStreamProducer:
    """
    AMQP Publisher that decouples GPS ingestion from database writes.
    Accepts high-frequency IoT GPS telematics and publishes to RabbitMQ topic exchange.
    """

    @classmethod
    def publish_ping(cls, ping_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publishes a GPS ping into the streaming message broker.
        Returns immediate acknowledgment with broker dispatch latency.
        """
        t0 = time.perf_counter()
        import pika

        category = ping_data.get('vehicle_category', 'general')
        routing_key = f"{ROUTING_KEY_PREFIX}.{category}"
        published = False

        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                connection_attempts=2,
                retry_delay=1,
                socket_timeout=2
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            # Declare durable topic exchange
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
            # Declare durable queue
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            # Bind queue to exchange
            channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=f"{ROUTING_KEY_PREFIX}.#")

            # Publish persistent JSON message
            body = json.dumps(ping_data)
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2, # make message persistent
                    content_type='application/json',
                    timestamp=int(time.time())
                )
            )
            connection.close()
            published = True
            STREAM_METRICS["broker_status"] = "connected"
            STREAM_METRICS["total_messages_published"] += 1
        except Exception as e:
            logger.warning(f"RabbitMQ publish fallback to direct pipeline: {e}")
            STREAM_METRICS["broker_status"] = "fallback_direct"
            # Fallback to direct synchronous ingestion if broker is temporarily down
            from operations.telemetry_pipeline import TelemetryIngestionPipeline
            direct_res = TelemetryIngestionPipeline.ingest_live_ping(**ping_data)
            direct_res["streaming_mode"] = "direct_fallback"
            return direct_res

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        STREAM_METRICS["last_publish_latency_ms"] = elapsed_ms

        return {
            "status": "queued_to_stream",
            "streaming_mode": "rabbitmq_amqp",
            "routing_key": routing_key,
            "broker_exchange": EXCHANGE_NAME,
            "latency_ms": elapsed_ms,
            "vehicle_id": ping_data.get('vehicle_id'),
            "registration_number": ping_data.get('registration_number'),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


class TelemetryStreamConsumer:
    """
    Decoupled Worker Consumer that drains GPS pings from RabbitMQ,
    evaluates safety guardrails, updates live radar, and flushes to PostGIS partitions.
    """

    @classmethod
    def consume_single_batch(cls, max_messages: int = 50) -> Dict[str, Any]:
        """
        Pulls a micro-batch of messages from the RabbitMQ queue and commits to PostGIS.
        """
        import pika
        from operations.telemetry_pipeline import TelemetryIngestionPipeline

        consumed_records = []
        alerts_detected = []

        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                socket_timeout=2
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            for _ in range(max_messages):
                method_frame, header_frame, body = channel.basic_get(queue=QUEUE_NAME, auto_ack=True)
                if not method_frame:
                    break

                STREAM_METRICS["total_messages_consumed"] += 1
                payload = json.loads(body.decode('utf-8'))
                res = TelemetryIngestionPipeline.ingest_live_ping(**payload)
                consumed_records.append(res)
                if res.get('alerts_triggered'):
                    alerts_detected.extend(res['alerts_triggered'])

            connection.close()
        except Exception as e:
            logger.error(f"Error draining telemetry stream: {e}")
            return {"status": "error", "message": str(e), "consumed_count": len(consumed_records)}

        # Flush any batched points to PostGIS partitioned historical table
        flush_res = TelemetryIngestionPipeline.flush_telemetry_batch()

        return {
            "status": "batch_consumed",
            "consumed_count": len(consumed_records),
            "alerts_triggered_count": len(alerts_detected),
            "alerts": alerts_detected,
            "postgis_flush": flush_res
        }
