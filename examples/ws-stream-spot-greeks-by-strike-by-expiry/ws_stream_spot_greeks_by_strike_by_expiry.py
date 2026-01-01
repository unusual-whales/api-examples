import websockets  # pip install websockets
import duckdb  # pip install duckdb
import asyncio
import json
import os
import random
import logging
import signal
import pyarrow as pa  # pip install pyarrow
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv  # pip install python-dotenv
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)  # .env in top-level directory

# DuckDB configuration details
DB_PATH = Path("spot_greeks_by_strike_by_expiry.duckdb")

# Tickers to monitor
TICKERS = ["SPY", "NFLX", "TSLA", "GOOGL"]

# Reconnection details
TIMEOUT_LENGTH = 90  # Timeout for receiving messages in seconds
MAX_RECONNECT_ATTEMPTS = 5  # Max number of reconnection attempts
RECONNECT_DELAY = 5  # Base delay between reconnection attempts in seconds
RECONNECT_DELAY_MAX = 60  # Maximum delay between reconnection attempts

# Batch configuration
BATCH_SIZE = 500  # Flush to DB every N records
BATCH_TIMEOUT = 10  # Flush to DB every N seconds (whichever comes first)

# Global flag for graceful shutdown
shutdown_flag = False


def setup_logging(
    logger_name: str="spot_greeks_by_strike_by_expiry",
    log_level: int=logging.DEBUG,
    log_file: str="spot_greeks_by_strike_by_expiry.log",
    max_bytes: int=5 * 1024 * 1024,  # 5 MB
    backup_count: int=5
) -> logging.Logger:
    """
    Set up logging configuration with file handler only.
    
    Args:
        logger_name (string): Name of the logger
        log_level (int): Logging level for both the logger and handlers
        log_file (string): Path to the log file
        max_bytes (int): Maximum size of each log file before rotation
        backup_count (int): Number of backup log files to keep
        
    Returns:
        logging.Logger: Configured Logger instance
    """
    logger = logging.getLogger(logger_name)

    # Initial logger config
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    logger.setLevel(log_level)
    log_format = logging.Formatter("%(asctime)s|%(name)s|%(levelname)s|%(message)s")

    # Create and configure file handler
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    # Prevent propagation to the root logger if needed
    logger.propagate = False
    
    return logger


def setup_database(db_path: Path = DB_PATH):
    """
    Create DuckDB database for aggregate spot greeks by strike by expiry data.

    Args:
        db_path (Path): path of the DuckDB database file

    Returns:
        None, creates the database file if it doesn't exist
    """
    conn = duckdb.connect(str(db_path))
    query = """
        CREATE TABLE IF NOT EXISTS spot_greeks_by_strike_by_expiry (
            -- Core dimensions
            ticker VARCHAR NOT NULL,
            expiry DATE NOT NULL,
            strike_price DOUBLE NOT NULL,
            strike_price_cents INTEGER NOT NULL,

            -- Timestamps
            timestamp_ms BIGINT NOT NULL,
            timestamp_dt TIMESTAMP NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,

            -- Market data
            underlying_price DOUBLE NOT NULL,

            -- Greeks by open interest
            call_delta_oi DOUBLE,
            put_delta_oi DOUBLE,
            call_gamma_oi DOUBLE,
            put_gamma_oi DOUBLE,
            call_charm_oi DOUBLE,
            put_charm_oi DOUBLE,
            call_vanna_oi DOUBLE,
            put_vanna_oi DOUBLE,

            -- Greeks by intraday volume
            call_delta_vol DOUBLE,
            put_delta_vol DOUBLE,
            call_gamma_vol DOUBLE,
            put_gamma_vol DOUBLE,
            call_charm_vol DOUBLE,
            put_charm_vol DOUBLE,
            call_vanna_vol DOUBLE,
            put_vanna_vol DOUBLE,

            -- Greeks by ask-side volume
            call_gamma_ask_vol DOUBLE,
            call_gamma_bid_vol DOUBLE,
            put_gamma_ask_vol DOUBLE,
            put_gamma_bid_vol DOUBLE,
            call_charm_ask_vol DOUBLE,
            call_charm_bid_vol DOUBLE,
            put_charm_ask_vol DOUBLE,
            put_charm_bid_vol DOUBLE,
            call_vanna_ask_vol DOUBLE,
            call_vanna_bid_vol DOUBLE,
            put_vanna_ask_vol DOUBLE,
            put_vanna_bid_vol DOUBLE,

            -- Deduplication key
            option_key VARCHAR NOT NULL,

            -- Metadata
            inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Primary key (for deduplication)
            PRIMARY KEY (option_key)
        );
    """
    conn.execute(query)
    
    # Create indexes for common query patterns
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ticker_date 
        ON spot_greeks_by_strike_by_expiry(ticker, date);
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_expiry 
        ON spot_greeks_by_strike_by_expiry(expiry);
    """)
    
    conn.close()
    logger = logging.getLogger("spot_greeks_by_strike_by_expiry")
    logger.info(f"Database initialized at {db_path}")


def validate_payload(payload: Dict[str, Any]) -> bool:
    """
    Validate that the payload contains required fields.
    
    Args:
        payload: Raw websocket message payload (dict)
        
    Returns:
        True if valid data message, False otherwise
    """
    if not isinstance(payload, dict):
        return False
    if "status" in payload and "timestamp" not in payload:
        return False
    if "timestamp" not in payload or "ticker" not in payload:
        return False
    
    return True


def parse_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a validated websocket message payload into database-ready format.

    Args:
        payload (dict): Validated websocket message payload
        
    Returns:
        Dict with transformed data ready for insertion
    """
    # Parse fields then build record
    timestamp_ms = int(payload["timestamp"])
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    strike = float(payload["strike"])
    strike_price_cents = int(round(strike * 100))
    option_key = f"{payload['ticker']}|{payload['expiry']}|{strike_price_cents}|{timestamp_ms}"
    
    record = {
        "ticker": payload["ticker"],
        "expiry": payload["expiry"],
        "strike_price": strike,
        "strike_price_cents": strike_price_cents,
        "timestamp_ms": timestamp_ms,
        "timestamp_dt": dt,
        "date": dt.date(),
        "time": dt.time(),
        "underlying_price": float(payload["price"]),
        
        # Greeks by open interest
        "call_delta_oi": float(payload.get("call_delta_oi", 0)),
        "put_delta_oi": float(payload.get("put_delta_oi", 0)),
        "call_gamma_oi": float(payload.get("call_gamma_oi", 0)),
        "put_gamma_oi": float(payload.get("put_gamma_oi", 0)),
        "call_charm_oi": float(payload.get("call_charm_oi", 0)),
        "put_charm_oi": float(payload.get("put_charm_oi", 0)),
        "call_vanna_oi": float(payload.get("call_vanna_oi", 0)),
        "put_vanna_oi": float(payload.get("put_vanna_oi", 0)),
        
        # Greeks by intraday volume
        "call_delta_vol": float(payload.get("call_delta_vol", 0)),
        "put_delta_vol": float(payload.get("put_delta_vol", 0)),
        "call_gamma_vol": float(payload.get("call_gamma_vol", 0)),
        "put_gamma_vol": float(payload.get("put_gamma_vol", 0)),
        "call_charm_vol": float(payload.get("call_charm_vol", 0)),
        "put_charm_vol": float(payload.get("put_charm_vol", 0)),
        "call_vanna_vol": float(payload.get("call_vanna_vol", 0)),
        "put_vanna_vol": float(payload.get("put_vanna_vol", 0)),
        
        # Greeks by ask/bid volume
        "call_gamma_ask_vol": float(payload.get("call_gamma_ask_vol", 0)),
        "call_gamma_bid_vol": float(payload.get("call_gamma_bid_vol", 0)),
        "put_gamma_ask_vol": float(payload.get("put_gamma_ask_vol", 0)),
        "put_gamma_bid_vol": float(payload.get("put_gamma_bid_vol", 0)),
        "call_charm_ask_vol": float(payload.get("call_charm_ask_vol", 0)),
        "call_charm_bid_vol": float(payload.get("call_charm_bid_vol", 0)),
        "put_charm_ask_vol": float(payload.get("put_charm_ask_vol", 0)),
        "put_charm_bid_vol": float(payload.get("put_charm_bid_vol", 0)),
        "call_vanna_ask_vol": float(payload.get("call_vanna_ask_vol", 0)),
        "call_vanna_bid_vol": float(payload.get("call_vanna_bid_vol", 0)),
        "put_vanna_ask_vol": float(payload.get("put_vanna_ask_vol", 0)),
        "put_vanna_bid_vol": float(payload.get("put_vanna_bid_vol", 0)),
        
        "option_key": option_key
    }
    
    return record


def flush_buffer_to_db(buffer: List[Dict[str, Any]], db_path: Path = DB_PATH) -> int:
    if not buffer:
        return 0
    
    logger = logging.getLogger("spot_greeks_by_strike_by_expiry")
    conn = duckdb.connect(str(db_path))
    
    try:
        # PyArrow Table insert (using explicity column list) is convenient with DuckDB
        arrow_table = pa.Table.from_pylist(buffer)
        columns = ", ".join(arrow_table.column_names)
        
        query = f"""
            INSERT OR IGNORE INTO spot_greeks_by_strike_by_expiry ({columns})
            SELECT * FROM arrow_table
        """
        conn.execute(query)
        
        rows_inserted = len(buffer)
        logger.info(f"Flushed {rows_inserted} records to database")
        
        return rows_inserted
        
    except Exception as e:
        logger.error(f"Error flushing buffer to database: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return 0
    finally:
        conn.close()


async def stream_websocket_to_buffer(
    websocket,
    buffer: List[Dict[str, Any]],
    logger: logging.Logger
) -> None:
    """
    Stream messages from websocket into buffer.
    
    Args:
        websocket: Active websocket connection
        buffer: List to accumulate records
        logger: Logger instance
    """
    global shutdown_flag
    
    last_flush_time = datetime.now()
    message_count = 0
    data_message_count = 0
    skipped_message_count = 0
    
    try:
        while not shutdown_flag:
            # Wait for message with timeout
            raw_message = await asyncio.wait_for(
                websocket.recv(),
                timeout=TIMEOUT_LENGTH
            )
            
            # Parse message
            try:
                message = json.loads(raw_message)
                message_count += 1
                
                # Step 1: Extract Payload
                # expected format: ["channel_name", {payload_dict}]
                if not isinstance(message, list) or len(message) < 2:
                    logger.warning(f"Unexpected message structure: {str(message)[:100]}")
                    continue  # Jump back to while loop and wait for next message

                payload = message[1]

                # Step 2: Verify Payload
                if not validate_payload(payload):
                    skipped_message_count += 1
                    if skipped_message_count <= 5:  # Log first few skips (likely connection msgs)
                        logger.debug(f"Skipped non-data message: {str(payload)[:100]}")
                    continue  # Jump back to while loop and wait for next message

                # Step 3: Parse Payload
                record = parse_payload(payload)
                
                buffer.append(record)
                data_message_count += 1
                
                # Check if we should flush (size or time based)
                current_time = datetime.now()
                time_since_flush = (current_time - last_flush_time).total_seconds()
                
                if len(buffer) >= BATCH_SIZE or time_since_flush >= BATCH_TIMEOUT:
                    flush_buffer_to_db(buffer)
                    buffer.clear()
                    last_flush_time = current_time
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
                logger.error(f"Raw message: {raw_message[:500]}")  # Log problematic message
            except KeyError as e:
                logger.error(f"Missing expected field in payload: {e}")
                logger.error(f"Payload: {str(message)[:500]}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                logger.error(f"Payload type: {type(message)}, content: {str(message)[:500]}")
                
    except asyncio.TimeoutError:
        warning_message = f"No message received for {TIMEOUT_LENGTH} seconds"
        logger.warning(warning_message)
        
        info_message = (
            f"Stats before timeout: {data_message_count} data messages, "
            f"{message_count} total, {skipped_message_count} skipped"
        )
        logger.info(info_message)

        # Flush remaining buffer before timeout
        if buffer:
            logger.info(f"Flushing {len(buffer)} records due to timeout")
            flush_buffer_to_db(buffer)
            buffer.clear()
        raise
    
    except Exception as e:
        logger.error(f"Websocket streaming error: {e}")
        # Flush remaining buffer on error
        if buffer:
            logger.info(f"Flushing {len(buffer)} records due to error")
            flush_buffer_to_db(buffer)
            buffer.clear()
        raise


async def connect_and_stream(logger: logging.Logger) -> None:
    """
    Manage websocket connection with automatic reconnection.
    
    Args:
        logger: Logger instance
    """
    global shutdown_flag
    
    api_token = os.getenv("UW_TOKEN")
    if not api_token:
        logger.error("UW_TOKEN not found in environment")
        return
    
    # Construct websocket URL (adjust endpoint as needed)
    ws_url = f"wss://api.unusualwhales.com/socket?token={api_token}"
    
    reconnect_attempts = 0
    buffer = []
    
    while not shutdown_flag and reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
        try:
            logger.info(f"Connecting to websocket... (attempt {reconnect_attempts + 1})")
            
            async with websockets.connect(ws_url) as websocket:
                logger.info("Connected to websocket")
                reconnect_attempts = 0  # Reset on successful connection

                # Join channels
                for ticker in TICKERS:
                    join_msg = json.dumps({"msg_type": "join", "channel": f"gex_strike_expiry:{ticker}"})
                    await websocket.send(join_msg)
                    logger.info(f"Joined channel for ticker: {ticker}")
                
                # Stream messages to buffer
                await stream_websocket_to_buffer(websocket, buffer, logger)
                
        except asyncio.TimeoutError:
            logger.warning("Connection timed out, reconnecting...")
            reconnect_attempts += 1
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Connection closed: {e}, reconnecting...")
            reconnect_attempts += 1
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            reconnect_attempts += 1
        
        # Flush any remaining buffer before reconnecting
        if buffer:
            logger.info(f"Flushing {len(buffer)} remaining records before reconnect")
            flush_buffer_to_db(buffer)
            buffer.clear()
        
        if not shutdown_flag and reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            # Exponential backoff with jitter
            delay = min(
                RECONNECT_DELAY * (2 ** reconnect_attempts) + random.uniform(0, 1),
                RECONNECT_DELAY_MAX
            )
            logger.info(f"Waiting {delay:.1f}s before reconnection attempt...")
            await asyncio.sleep(delay)
    
    if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
        logger.error(f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_flag
    logger = logging.getLogger("spot_greeks_by_strike_by_expiry")
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True


async def main():
    """
    Main entry point for websocket streaming application.
    """
    # Setup logging
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("Starting Spot Greeks Websocket Streamer")
    logger.info("=" * 60)
    
    # Setup database
    setup_database()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start websocket streaming
        await connect_and_stream(logger)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        logger.info("Shutting down gracefully...")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
