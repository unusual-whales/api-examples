import httpx  # pip install httpx
import aiosqlite  # pip install aiosqlite
import asyncio
import json
import os
import random
import signal
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv  # pip install python-dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # pip install apscheduler
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)  # .env in top-level directory to load API token

@dataclass
class Security:
    ticker: str
    min_strike: int
    max_strike: int

# Set min_strike and max_strike to realistic limits if preferred
# otherwise set them extremely wide to collect data on all strikes
securities = [
    Security(ticker="SPXW", min_strike=0, max_strike=20000),
    Security(ticker="SPY", min_strike=0, max_strike=1000),
    Security(ticker="AAPL", min_strike=0, max_strike=1000),
    Security(ticker="TSLA", min_strike=0, max_strike=2000),
]

DB_PATH = Path("spot_greek_exposure_by_strike.db")
HEADERS = {
    "Accept": "application/json, text/plain",
    "Authorization": os.getenv("UW_TOKEN"),
}

def floatify(value) -> float | None:
    """Convert value to float, return None if conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def setup_logging(
    logger_name: str="spot_greek_exposure_by_strike",
    log_level: int=logging.DEBUG,
    log_file: str="spot_greek_exposure_by_strike.log",
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
    Create spot_greek_exposure_by_strike table if it does not exist.

    Args:
        db_path: Path to the SQLite database file
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS spot_greek_exposure_by_strike (
                api_access_datetime TEXT,
                page INTEGER,
                date TEXT,
                time TEXT,
                ticker TEXT,
                strike REAL,
                price REAL,
                call_delta_oi REAL,
                call_delta_vol REAL,
                call_delta_ask REAL,
                call_delta_bid REAL,
                put_delta_oi REAL,
                put_delta_vol REAL,
                put_delta_ask REAL,
                put_delta_bid REAL,
                call_gamma_oi REAL,
                call_gamma_vol REAL,
                call_gamma_ask REAL,
                call_gamma_bid REAL,
                put_gamma_oi REAL,
                put_gamma_vol REAL,
                put_gamma_ask REAL,
                put_gamma_bid REAL,
                call_vanna_oi REAL,
                call_vanna_vol REAL,
                call_vanna_ask REAL,
                call_vanna_bid REAL,
                put_vanna_oi REAL,
                put_vanna_vol REAL,
                put_vanna_ask REAL,
                put_vanna_bid REAL,
                call_charm_oi REAL,
                call_charm_vol REAL,
                call_charm_ask REAL,
                call_charm_bid REAL,
                put_charm_oi REAL,
                put_charm_vol REAL,
                put_charm_ask REAL,
                put_charm_bid REAL
            )
            """
        )
        await db.commit()

async def fetch_data_and_write_to_db(
    securities: list,
    db_path: str,
    logger: logging.Logger
):
    """
    Fetch spot greek exposure by strike data from UW API and write to SQLite database.

    Args:
        tickers: List of ticker symbols to fetch data for
        db_path: Path to the SQLite database file
    """
    results = []
    try:
        for security in securities:
            url = (
                f"https://api.unusualwhales.com/api/stock/"
                f"{security.ticker}/spot-exposures/strike"
            )
            response_is_good = True
            page = 0
            while response_is_good:
                params = {
                    "page": page,
                    "limit": 500,
                    "min_strike": security.min_strike,
                    "max_strike": security.max_strike,
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    rsp = await client.get(url, headers=HEADERS, params=params)
                    rsp.raise_for_status()
                    if (
                        rsp.status_code == 200 and
                        "data" in rsp.json() and
                        len(rsp.json()["data"]) > 0
                    ):
                        raw_data = rsp.json().get("data", [])
                        for record in raw_data:
                            results.append(
                                (
                                    datetime.now().isoformat(),
                                    page,
                                    record.get("date"),
                                    record.get("time"),
                                    record.get("ticker"),
                                    floatify(record.get("strike")),
                                    floatify(record.get("price")),
                                    floatify(record.get("call_delta_oi")),
                                    floatify(record.get("call_delta_vol")),
                                    floatify(record.get("call_delta_ask")),
                                    floatify(record.get("call_delta_bid")),
                                    floatify(record.get("put_delta_oi")),
                                    floatify(record.get("put_delta_vol")),
                                    floatify(record.get("put_delta_ask")),
                                    floatify(record.get("put_delta_bid")),
                                    floatify(record.get("call_gamma_oi")),
                                    floatify(record.get("call_gamma_vol")),
                                    floatify(record.get("call_gamma_ask")),
                                    floatify(record.get("call_gamma_bid")),
                                    floatify(record.get("put_gamma_oi")),
                                    floatify(record.get("put_gamma_vol")),
                                    floatify(record.get("put_gamma_ask")),
                                    floatify(record.get("put_gamma_bid")),
                                    floatify(record.get("call_vanna_oi")),
                                    floatify(record.get("call_vanna_vol")),
                                    floatify(record.get("call_vanna_ask")),
                                    floatify(record.get("call_vanna_bid")),
                                    floatify(record.get("put_vanna_oi")),
                                    floatify(record.get("put_vanna_vol")),
                                    floatify(record.get("put_vanna_ask")),
                                    floatify(record.get("put_vanna_bid")),
                                    floatify(record.get("call_charm_oi")),
                                    floatify(record.get("call_charm_vol")),
                                    floatify(record.get("call_charm_ask")),
                                    floatify(record.get("call_charm_bid")),
                                    floatify(record.get("put_charm_oi")),
                                    floatify(record.get("put_charm_vol")),
                                    floatify(record.get("put_charm_ask")),
                                    floatify(record.get("put_charm_bid")),
                                )
                            )
                        page += 1
                    else:
                        response_is_good = False

    except Exception as e:
        logger.error(f"Error occurred in data collection: {e}", exc_info=True)
        raise
            
    # Use explicit transaction with executemany for atomic batch insert
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("BEGIN TRANSACTION"):
                await db.executemany(
                    """
                    INSERT INTO spot_greek_exposure_by_strike (
                        api_access_datetime,
                        page,
                        date,
                        time,
                        ticker,
                        strike,
                        price,
                        call_delta_oi,
                        call_delta_vol,
                        call_delta_ask,
                        call_delta_bid,
                        put_delta_oi,
                        put_delta_vol,
                        put_delta_ask,
                        put_delta_bid,
                        call_gamma_oi,
                        call_gamma_vol,
                        call_gamma_ask,
                        call_gamma_bid,
                        put_gamma_oi,
                        put_gamma_vol,
                        put_gamma_ask,
                        put_gamma_bid,
                        call_vanna_oi,
                        call_vanna_vol,
                        call_vanna_ask,
                        call_vanna_bid,
                        put_vanna_oi,
                        put_vanna_vol,
                        put_vanna_ask,
                        put_vanna_bid,
                        call_charm_oi,
                        call_charm_vol,
                        call_charm_ask,
                        call_charm_bid,
                        put_charm_oi,
                        put_charm_vol,
                        put_charm_ask,
                        put_charm_bid
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
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    results
                )
                await db.commit()
                logger.info(
                    f"Successfully batch inserted ({len(results)} records) to DB"
                )
    except Exception as e:
        logger.error(f"Error occurred during DB insert: {e}", exc_info=True)
        raise
    
async def main():
    logger = setup_logging()
    logger.info("Starting spot greek exposure by strike main loop...")
    await create_database_table(str(DB_PATH))
    logger.info("Database table ensured")

    scheduler = AsyncIOScheduler(
        job_defaults={
            "coalesce": True,  # Combine missed executions
            "max_instances": 1,  # Prevent multiple instances
            "misfire_grace_time": 30  # Allow 30 seconds grace time for misfires
        }
    )

    # Initial fetch and write
    await fetch_data_and_write_to_db(securities, str(DB_PATH), logger)

    # Schedule future fetches
    scheduler.add_job(
        fetch_data_and_write_to_db,
        "interval",
        minutes=1,
        args=[securities, str(DB_PATH), logger],
    )
    logger.info("Starting scheduler...")
    scheduler.start()

    try:
        # Keep the main coroutine running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
