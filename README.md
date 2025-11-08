# Unusual Whales API Examples
A collection of heavily-commented sample scripts and notebooks demonstrating how to use the Unusual Whales API.

## Unusual Whales Links
- Docs: [https://api.unusualwhales.com/docs#/](https://api.unusualwhales.com/docs#/)
- Pricing: [https://unusualwhales.com/public-api#pricing](https://unusualwhales.com/public-api#pricing)
- How To Check Your API Usage: [https://unusualwhales.com/information/how-to-check-your-api-usage](https://unusualwhales.com/information/how-to-check-your-api-usage)
- **For users of LLM tools like ChatGPT, Claude, Gemini, etc.** How To Fix 404 Errors: [https://unusualwhales.com/information/how-to-fix-404-errors-when-using-ai-tools-with-the-unusual-whales-api](https://unusualwhales.com/information/how-to-fix-404-errors-when-using-ai-tools-with-the-unusual-whales-api)

## Examples

### Websocket: How to stream flow alerts into a local SQLite database
- `examples/ws-stream-flow-alerts-to-sqlite`
- This python script connects to the `flow-alerts` websocket channel and streams all Flow Alerts to a buffer and flushing to a SQLite database once per second. The folder contains example output files as well.

### Websocket: How to stream data from multiple channel and write to multiple outputs
- `examples/ws-multi-channel-multi-output`
- This python script connects to several different websocket channels (greeks, flow alerts, and all option trades for ticker `TSLA`). It writes results to multiple buffers and flushes those buffers to multiple files once per second. The folder contains example output files as well.

### Websocket: How to stream data from multiple channel and write to multiple outputs (javascript version)
- `examples/ws-multi-channel-multi-output-nodejs`
- Same as the above but implemented in javascript.

### Spot Greek Exposure by Strike
- `examples/spot-greek-exposure-by-strike`
- This python script collects spot greek exposure data by strike for multiple tickers and strike ranges once per minute then writes all results to a SQLite database. The folder contains example output files and basic data exploration queries.

### Earnings and Institutional Holdings
- `examples/earnings-with-known-institutional-holdings`
- This notebook collects upcoming earnings information and uses those tickers to analyze high-profile institutional holdings

### Market Tide
- `examples/market-tide`
- This notebook collects market tide and OHLC price data (for ticker `SPY`) then plots them

### Flow Alerts
- `examples/flow-alerts-multiple-tickers`
- This notebook interacts with the Flow Alerts endpoint to collect filtered data then further refines the results
- Watch Dan build an earlier version of this same notebook from scratch on Youtube: [https://www.youtube.com/watch?v=pzLo5NqyEQo](https://www.youtube.com/watch?v=pzLo5NqyEQo)

### Top Net Impact Chart
- `examples/replicate-top-net-impact-chart`
- This notebook collects data from the powerful Stock Screener endpoint then filters those results to find the biggest net bullish and net bearish impacts before finally plotting them as a bar chart

### Net Premium Ticks Dashboard
- `examples/net-prem-ticks-dashboard`
- This notebook gets net premium ticks and OHLC data for a group of tickers then constructs a dashboard of "thumbnail"-type interactive charts for each, allowing the user to monitor premium flow across many tickers easily
