import websockets  # pip install websockets
import aiofiles  # pip install aiofiles
import asyncio
import json
import os
import signal
import random
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv  # pip install python-dotenv
from pathlib import Path
from datetime import datetime
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)  # .env in top-level directory

# Reconnection details
TIMEOUT_LENGTH = 30  # Timeout for receiving messages in seconds
MAX_RECONNECT_ATTEMPTS = 5  # Max number of reconnection attempts
RECONNECT_DELAY = 5  # Base delay between reconnection attempts in seconds
RECONNECT_DELAY_MAX = 60  # Maximum delay between reconnection attempts


def get_now_datetime() -> str:
    """
    Generate a formatted string of the current datetime.

    Args:
        None

    Returns:
        str: Current datetime formatted as "YYYY-MM-DD HH:MM:SS.microseconds"
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def setup_logging(
    logger_name: str = 'ws_demo',
    log_level: int = logging.DEBUG,
    log_file: str = 'demo_log.log',
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up logging configuration with both console and file handlers.
    
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
    log_format = logging.Formatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s')
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    
    # Create and configure file handler
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Prevent propagation to the root logger if needed
    logger.propagate = False
    
    return logger


async def flush_buffers(file_and_buffer_pairs: dict):
    """
    Flush all buffers to their respective files.

    Args:
        file_and_buffer_pairs: Dictionary mapping file handlers to their buffers

    Returns:
        None
    """
    for f, buffer in file_and_buffer_pairs.items():
        for msg in buffer:
            await f.write(msg)
        await f.flush()  # Write to disk


async def connect_websocket():
    """
    Establish WebSocket connection to Unusual Whales API and subscribe to
    various channels. Received data is written to text files.

    Args:
        None
    Returns:
        None
    """
    # Get API token from environment variables
    uw_api_token = os.getenv('UW_TOKEN')  # or replace with your token
    uri = f'wss://api.unusualwhales.com/socket?token={uw_api_token}'

    # Get a logger instance
    logger = setup_logging()
    
    # Create a unique filename based on current timestamp
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file_optiontrades = f'demo_optiontrades_{ts}.txt'
    out_file_greeks = f'demo_greeks_{ts}.txt'
    out_file_flowalerts = f'demo_flowalerts_{ts}.txt'
    
    # Variable to track when we last flushed data to disk
    last_flush_time = datetime.now()
    # Buffer to store messages between flushes
    message_buffer_optiontrades = []
    message_buffer_greeks = []
    message_buffer_flowalerts = []

    async with (
        aiofiles.open(out_file_optiontrades, 'a') as f_optiontrades,
        aiofiles.open(out_file_greeks, 'a') as f_greeks,
        aiofiles.open(out_file_flowalerts, 'a') as f_flowalerts,
    ):
        try:
            # Establish WebSocket connection
            async with websockets.connect(uri) as ws:
                # List of channels we want to join
                channels = [
                    {'channel': 'option_trades:TSLA', 'msg_type': 'join'},
                    {'channel': 'gex:SPY', 'msg_type': 'join'},
                    {'channel': 'gex:QQQ', 'msg_type': 'join'},
                    {'channel': 'gex:IWM', 'msg_type': 'join'},
                    {'channel': 'flow-alerts', 'msg_type': 'join'},
                ]
                
                # Join each channel in the WebSocket connection
                for msg in channels:
                    await ws.send(json.dumps(msg))
                    logger.info(f'Connected and joined {msg["channel"]} channel')
                
                try:
                    # Main loop to receive messages
                    while True:
                        try:
                            # Wait for and receive the next message
                            message = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_LENGTH)
                            data = json.loads(message)
                            channel, payload = data
                            
                            # Format the message with timestamp
                            formatted_message = (
                                f'{get_now_datetime()}'
                                f'|{channel}|{payload}\n'
                            )
                            
                            # Add message to buffer
                            if 'option_trades' in channel:
                                message_buffer_optiontrades.append(formatted_message)
                            elif 'flow-alerts' in channel:
                                message_buffer_flowalerts.append(formatted_message)
                            elif 'gex' in channel:
                                message_buffer_greeks.append(formatted_message)
                            else:
                                logger.error(f'Unknown channel: {channel}|{formatted_message}')
                            
                            # Check if it's time to flush data (every 1 second)
                            current_time = datetime.now()
                            time_since_flush = (current_time - last_flush_time).total_seconds()
                            
                            if time_since_flush >= 1.0:  # 1 second flush interval
                                files_and_buffers = {
                                    f_optiontrades: message_buffer_optiontrades,
                                    f_flowalerts: message_buffer_flowalerts,
                                    f_greeks: message_buffer_greeks,
                                }
                                await flush_buffers(files_and_buffers)
                                
                                # Reset buffer and update last flush time
                                message_buffer_optiontrades = []
                                message_buffer_flowalerts = []
                                message_buffer_greeks = []
                                last_flush_time = current_time
                    
                        except asyncio.TimeoutError:
                            # No message received within timeout, check connection
                            logger.info(f'No messages received for {TIMEOUT_LENGTH}s, '
                                        f'checking connection...')
                            try:
                                # Send a ping to check if connection is still alive
                                pong = await ws.ping()
                                await asyncio.wait_for(pong, timeout=10)
                                logger.info('Connection is still alive')
                            except:
                                logger.warning('Connection appears to be dead, '
                                               'raising exception to reconnect')
                                raise websockets.exceptions.ConnectionClosed(
                                    1006, 'Connection timed out'
                                )
                            
                            # Flush buffers during quiet periods
                            files_and_buffers = {
                                f_optiontrades: message_buffer_optiontrades,
                                f_flowalerts: message_buffer_flowalerts,
                                f_greeks: message_buffer_greeks,
                            }
                            await flush_buffers(files_and_buffers)
                                
                            # Reset buffer and update last flush time
                            message_buffer_optiontrades = []
                            message_buffer_flowalerts = []
                            message_buffer_greeks = []
                            last_flush_time = datetime.now()
                            
                except asyncio.CancelledError:   
                    # Log when connection is being closed due to cancellation
                    logger.info('Close connection instruction received')
                                        
                    # Flush any remaining buffered data
                    files_and_buffers = {
                        f_optiontrades: message_buffer_optiontrades,
                        f_flowalerts: message_buffer_flowalerts,
                        f_greeks: message_buffer_greeks,
                    }
                    await flush_buffers(files_and_buffers)
                    await ws.close()
                    raise  # Propogate to signal task cancellation

                except websockets.exceptions.ConnectionClosed as e:
                    # Connection closed, log it and let reconnection logic handle it
                    logger.warning(f'Connection closed: {e}')

                    # Flush any remaining buffered data
                    files_and_buffers = {
                        f_optiontrades: message_buffer_optiontrades,
                        f_flowalerts: message_buffer_flowalerts,
                        f_greeks: message_buffer_greeks,
                    }
                    await flush_buffers(files_and_buffers)
                    raise  # Propagate the exception to trigger reconnection

                except Exception as e:
                    # Log any unexpected errors
                    logger.error(f'Error occurred: {e}')

                    # Flush any remaining buffered data
                    files_and_buffers = {
                        f_optiontrades: message_buffer_optiontrades,
                        f_flowalerts: message_buffer_flowalerts,
                        f_greeks: message_buffer_greeks,
                    }
                    await flush_buffers(files_and_buffers)
                    raise  # Propagate the exception to trigger reconnection
        
        except Exception as e:
            logger.error(f'Error in WebSocket connection: {e}')
            raise  # Propagate the exception to trigger reconnection


async def main():
    """
    Main function to start the WebSocket connection task
    and handle graceful shutdown with reconnection logic.
    """
    logger = setup_logging()
    reconnect_attempt = 0
    running = True
    
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
            
            logger.info(f'Reconnection attempt {reconnect_attempt} of'
                        f' {MAX_RECONNECT_ATTEMPTS} after waiting'
                        f' {reconnect_delay:.2f} seconds...')
            await asyncio.sleep(reconnect_delay)
        
        # Create a task for the WebSocket connection
        task = asyncio.create_task(connect_websocket())
        
        try:
            # Wait for the task to complete
            await task
            # If we reached here, the WebSocket connection closed normally
            logger.info('WebSocket connection closed normally')
            running = False  # No need to reconnect if connection closed normally
            
        except asyncio.CancelledError:
            # Handle cancellation (without keyboard interrupt)
            logger.info('Application shutdown requested')
            running = False  # Stop the reconnection loop
            
        except KeyboardInterrupt:
            # Handle keyboard interruption (Ctrl+C)
            logger.info('Gracefully shutting down based on keyboard exit')
            running = False  # Stop the reconnection loop
            # Cancel the WebSocket connection task
            task.cancel()
            try:
                # Wait for the task to be properly cancelled
                await task
            except asyncio.CancelledError:
                logger.info('Application shutdown complete')
                
        except Exception as e:
            # Handle unexpected errors and try to reconnect
            logger.error(f'Unexpected error in main loop: {e}')
            reconnect_attempt += 1
            
    # If MAX_RECONNECT_ATTEMPTS reached
    if reconnect_attempt > MAX_RECONNECT_ATTEMPTS:
        logger.error(f'Maximum reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) '
                     f'reached. Giving up.')


if __name__ == '__main__':
    # Run the main function using asyncio
    asyncio.run(main())
