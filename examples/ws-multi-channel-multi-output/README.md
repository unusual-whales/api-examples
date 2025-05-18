# Multi-channel Multi-outfile Websocket Example
This python script demonstrates some of the most popular websocket functionality:
- Connect to multiple channels including ticker-specific greeks and market-wide flow alerts
- Connect to the "full ocean" of transaction-level option trades for ticker `TSLA`
- Use buffers to temporarily store data before writing to files every 1 second
- Write to different files depending on the data
- Automatic reconnect (tries 5 times before it quits)

### Notes
- `get_now_datetime()`: convenience function for string-formatted datetime
- `setup_logging()`: creates and configures the `logger`
- `async flush_buffers()`: write messages from buffers to disk
- `async connect_websocket()`: the key function that interacts with the Unusual Whales websocket, if you are starting from this demo script then the adjustments you will make are almost certainly going to be in this function
- `async main()`: the main loop
