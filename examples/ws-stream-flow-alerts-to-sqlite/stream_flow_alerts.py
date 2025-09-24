import websockets  # pip install websockets
import aiosqlite  # pip install aiosqlite
import asyncio
import json
import os
import random
import logging
import signal
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv  # pip install python-dotenv
from pathlib import Path
from datetime import datetime
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)  # .env in top-level directory

# Reconnection details
TIMEOUT_LENGTH = 30  # Timeout for receiving messages in seconds
MAX_RECONNECT_ATTEMPTS = 5  # Max number of reconnection attempts
RECONNECT_DELAY = 5  # Base delay between reconnection attempts in seconds
RECONNECT_DELAY_MAX = 60  # Maximum delay between reconnection attempts

def setup_logging(
    logger_name: str="flow_alerts",
    log_level: int=logging.DEBUG,
    log_file: str="flow_alerts.log",
    max_bytes: int=5 * 1024 * 1024,  # 5 MB
    backup_count: int=5
) -> logging.Logger:
    """
    Set up logging configuration with file handler only.
    
    Args:
        logger_name: Name of the logger
        log_level: Logging level for both the logger and handlers
        log_file: Path to the log file
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured Logger instance
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

async def create_database_table(db_path: str):
    """
    Create the flow_alerts table if it does not exist.
    
    Args:
        db_path: Path to the SQLite database file
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS flow_alerts (
                rule_id TEXT,
                rule_name TEXT,
                ticker TEXT,
                option_chain TEXT,
                underlying_price REAL,
                volume INTEGER,
                total_size INTEGER,
                total_premium REAL,
                total_ask_side_prem REAL,
                total_bid_side_prem REAL,
                start_time INTEGER,
                end_time INTEGER,
                url TEXT,
                price REAL,
                has_multileg BOOLEAN,
                has_sweep BOOLEAN,
                has_floor BOOLEAN,
                open_interest INTEGER,
                all_opening_trades BOOLEAN,
                id TEXT PRIMARY KEY,
                has_singleleg BOOLEAN,
                volume_oi_ratio REAL,
                trade_ids TEXT,
                trade_count INTEGER,
                expiry_count INTEGER,
                executed_at INTEGER,
                ask_vol INTEGER,
                bid_vol INTEGER,
                no_side_vol INTEGER,
                mid_vol INTEGER,
                multi_vol INTEGER,
                stock_multi_vol INTEGER,
                upstream_condition_details TEXT,
                exchanges TEXT,
                bid REAL,
                ask REAL
            )
            """
        )
        await db.commit()

async def flush_buffers_to_db(db_path: str, message_buffer: list):
    """
    Flush all buffered messages to the SQLite database using batch inserts.

    Args:
        db_path: Path to the SQLite database file
        message_buffer: List of payload dictionaries to insert
    """
    logger = setup_logging()

    if not message_buffer:
        return
    
    async with aiosqlite.connect(db_path) as db:
        try:
            batch_data = []
            for payload in message_buffer:
                # Convert arrays to JSON strings for storage
                trade_ids = json.dumps(payload.get("trade_ids", []))
                upstream_condition_details = json.dumps(
                    payload.get("upstream_condition_details", [])
                )
                exchanges = json.dumps(payload.get("exchanges", []))

                batch_data.append(
                    (
                        payload.get("rule_id"),
                        payload.get("rule_name"),
                        payload.get("ticker"),
                        payload.get("option_chain"),
                        payload.get("underlying_price"),
                        payload.get("volume"),
                        payload.get("total_size"),
                        payload.get("total_premium"),
                        payload.get("total_ask_side_prem"),
                        payload.get("total_bid_side_prem"),
                        payload.get("start_time"),
                        payload.get("end_time"),
                        payload.get("url"),
                        payload.get("price"),
                        payload.get("has_multileg"),
                        payload.get("has_sweep"),
                        payload.get("has_floor"),
                        payload.get("open_interest"),
                        payload.get("all_opening_trades"),
                        payload.get("id"),
                        payload.get("has_singleleg"),
                        payload.get("volume_oi_ratio"),
                        trade_ids,
                        payload.get("trade_count"),
                        payload.get("expiry_count"),
                        payload.get("executed_at"),
                        payload.get("ask_vol"),
                        payload.get("bid_vol"),
                        payload.get("no_side_vol"),
                        payload.get("mid_vol"),
                        payload.get("multi_vol"),
                        payload.get("stock_multi_vol"),
                        upstream_condition_details,
                        exchanges,
                        float(payload.get("bid", 0)),
                        float(payload.get("ask", 0)),
                    )
                )

            # Use explicit transaction with executemany for atomic batch insert
            async with db.execute("BEGIN TRANSACTION"):
                await db.executemany(
                    """
                    INSERT INTO flow_alerts (
                        rule_id,
                        rule_name,
                        ticker,
                        option_chain,
                        underlying_price,
                        volume,
                        total_size,
                        total_premium,
                        total_ask_side_prem,
                        total_bid_side_prem,
                        start_time,
                        end_time,
                        url,
                        price,
                        has_multileg,
                        has_sweep,
                        has_floor,
                        open_interest,
                        all_opening_trades,
                        id,
                        has_singleleg,
                        volume_oi_ratio,
                        trade_ids,
                        trade_count,
                        expiry_count,
                        executed_at,
                        ask_vol,
                        bid_vol,
                        no_side_vol,
                        mid_vol,
                        multi_vol,
                        stock_multi_vol,
                        upstream_condition_details,
                        exchanges,
                        bid,
                        ask
                    ) VALUES (
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?, 
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?, 
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?, 
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    batch_data
                )
                await db.commit()
                logger.info(
                    f"Successfully batch inserted ({len(message_buffer)} records) to DB"
                )
        except Exception as e:
            logger.error(
                f"Error batch inserting ({len(message_buffer)} records) to DB: {e}"
            )
            raise

async def connect_websocket():
    """
    Establish WebSocket connection to Unusual Whales API and subscribe to
    various channels. Received data is written to SQLite database.
    """
    logger = setup_logging()
    uw_api_token = os.getenv("UW_TOKEN")  # or replace with your token
    uri = f"wss://api.unusualwhales.com/socket?token={uw_api_token}"

    db_path = Path("flow_alerts.db")
    await create_database_table(str(db_path))
    
    # Create message buffer and start flush timer
    last_flush_time = datetime.now()
    message_buffer = []

    try:
        async with websockets.connect(uri) as ws:
            # List of websocket channels we want to join
            channels = [
                {"channel": "flow-alerts", "msg_type": "join"},
            ]
            
            for msg in channels:
                await ws.send(json.dumps(msg))
                logger.info(f"Connected and joined {msg['channel']} channel")

            try:
                # Main loop to receive messages
                while True:
                    try:
                        message = await asyncio.wait_for(
                            ws.recv(),
                            timeout=TIMEOUT_LENGTH
                        )
                        data = json.loads(message)
                        channel, payload = data
                        
                        if "flow-alerts" in channel:
                            message_buffer.append(payload)
                        else:
                            logger.error(f"Unknown channel: {channel}")

                        # Check if it is time to flush data (every 1 second)
                        current_time = datetime.now()
                        time_since_flush = (
                            current_time - last_flush_time
                        ).total_seconds()
                        
                        if time_since_flush >= 1.0:
                            await flush_buffers_to_db(str(db_path), message_buffer)
                            message_buffer = []
                            last_flush_time = current_time
                
                    except asyncio.TimeoutError:
                        # No message received within timeout, check connection
                        logger.info(f"No messages received for {TIMEOUT_LENGTH}s, "
                                    f"checking connection...")
                        try:
                            # Send a ping to check if connection is still alive
                            pong = await ws.ping()
                            await asyncio.wait_for(pong, timeout=10)
                            logger.info("Connection is still alive")
                        except:
                            logger.warning("Connection appears to be dead, "
                                           "raising exception to reconnect")
                            raise websockets.exceptions.ConnectionClosed(
                                1006, "Connection timed out"
                            )
                        
                        # Flush buffers during quiet periods
                        await flush_buffers_to_db(str(db_path), message_buffer)
                        message_buffer = []
                        last_flush_time = datetime.now()

                    except (
                        ConnectionResetError,
                        websockets.exceptions.ConnectionClosedError
                    ) as e:
                        # Connection was reset by peer or closed unexpectedly
                        logger.warning(f"Connection lost: {e}")
                        # Flush any remaining buffered data
                        await flush_buffers_to_db(str(db_path), message_buffer)
                        raise  # Propagate the exception to trigger reconnection
                        
            except asyncio.CancelledError:   
                # Log when connection is being closed due to cancellation
                logger.info("Close connection instruction received")
                                
                # Flush any remaining buffered data
                await flush_buffers_to_db(str(db_path), message_buffer)
                await ws.close()
                raise  # Propagate to signal task cancellation

            except websockets.exceptions.ConnectionClosed as e:
                # Connection closed, log it and let reconnection logic handle it
                logger.warning(f"Connection closed: {e}")

                # Flush any remaining buffered data
                await flush_buffers_to_db(str(db_path), message_buffer)
                raise  # Propagate the exception to trigger reconnection

            except (ConnectionResetError, websockets.exceptions.ConnectionClosedError) as e:
                # Handle connection reset/closed at the outer level too
                logger.warning(f"WebSocket connection lost: {e}")
                # Flush any remaining buffered data
                await flush_buffers_to_db(str(db_path), message_buffer)
                raise  # Propagate the exception to trigger reconnection

            except Exception as e:
                # Log any unexpected errors
                logger.error(f"Error occurred: {e}")

                # Flush any remaining buffered data
                await flush_buffers_to_db(str(db_path), message_buffer)
                raise  # Propagate the exception to trigger reconnection
    
    except (ConnectionResetError, websockets.exceptions.ConnectionClosedError) as e:
        # Handle connection errors at the top level
        logger.warning(f"Failed to establish or maintain WebSocket connection: {e}")
        raise  # Propagate the exception to trigger reconnection
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        raise  # Propagate the exception to trigger reconnection

async def main():
    """
    Main function to start the WebSocket connection task, scheduler,
    and handle graceful shutdown with reconnection logic.
    """
    logger = setup_logging()
    reconnect_attempt = 0
    running = True
    
    # Create shutdown event
    shutdown_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)
    
    while running and reconnect_attempt <= MAX_RECONNECT_ATTEMPTS:
        if reconnect_attempt > 0:
            # Calculate exponential backoff delay (with jitter)
            delay = min(
                RECONNECT_DELAY * (2 ** (reconnect_attempt - 1)),
                RECONNECT_DELAY_MAX
            )
            # Add a small random value to avoid reconnection storms
            jitter = delay * 0.1 * random.random()
            reconnect_delay = delay + jitter
            
            logger.info(
                f"Reconnection attempt {reconnect_attempt} of"
                f" {MAX_RECONNECT_ATTEMPTS} after waiting"
                f" {reconnect_delay:.2f} seconds..."
            )
            
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=reconnect_delay)
                logger.info("Shutdown requested during reconnection delay")
                running = False
                break
            except asyncio.TimeoutError:
                pass  # Continue with reconnection
        
        # Create a task for the WebSocket connection
        task = asyncio.create_task(connect_websocket())
        
        try:
            # Wait for either the task to complete or shutdown signal
            done, pending = await asyncio.wait(
                [task, asyncio.create_task(shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if shutdown_event.is_set():
                logger.info("Gracefully shutting down...")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info("WebSocket task cancelled successfully")
                running = False
                break
            else:
                # WebSocket task completed normally
                logger.info("WebSocket connection closed normally")
                running = False
                
        except Exception as e:
            # Handle unexpected errors and try to reconnect
            logger.error(f"Unexpected error in main loop: {e}")
            reconnect_attempt += 1
            
    if reconnect_attempt > MAX_RECONNECT_ATTEMPTS:
        logger.error(
            f"Maximum reconnection attempts ({MAX_RECONNECT_ATTEMPTS})"
            f" reached. Giving up."
        )
    
    logger.info("Application shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
