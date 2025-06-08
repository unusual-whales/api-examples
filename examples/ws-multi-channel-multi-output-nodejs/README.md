# Unusual Whales WebSocket Client for Node.js

A production-ready WebSocket client for streaming real-time financial data from the Unusual Whales API. Features automatic reconnection, buffered file output, and comprehensive error handling.

## Features

- **Automatic Reconnection**: Exponential backoff with jitter (5s to 60s max delay)
- **Multi-Channel Support**: Subscribes to option trades, Greeks (GEX), and flow alerts
- **Buffered File Writing**: Separate timestamped output files per channel
- **Connection Health Monitoring**: 30-second timeout with ping/pong health checks
- **Graceful Shutdown**: Proper cleanup and data flushing on exit
- **Event-Driven Architecture**: EventEmitter pattern for real-time monitoring
- **Memory Leak Prevention**: Proper resource cleanup and timer management

## Installation

```bash
npm install
```

## Setup

1. **Get your Unusual Whales API token** from [unusualwhales.com](https://unusualwhales.com/)

2. **Create environment file**:
   ```bash
   cp .env.example .env
   ```

3. **Add your API token** to `.env`:
   ```
   UW_TOKEN=your_unusual_whales_api_token_here
   ```

## Usage

### Quick Start

```bash
npm run uw-client
```

Or run directly:

```bash
node uw_websocket_client.js
```

### Basic Example

```javascript
const UnusualWhalesClient = require('./uw_websocket_client');

const client = new UnusualWhalesClient();

// Optional: Set up event listeners
client.on('connected', () => console.log('Connected!'));
client.on('disconnected', () => console.log('Disconnected'));
client.on('message', (data) => {
    console.log(`Received ${data.channel} data`);
});

// Start streaming
client.start().catch(console.error);
```

## Data Channels

The client subscribes to multiple financial data channels:

### Option Trades
- **Channel**: `option_trades:TSLA`
- **Output File**: `demo_optiontrades_YYYYMMDD_HHMMSS.txt`
- **Data**: Real-time Tesla option trade data

### Greeks Exposure (GEX)
- **Channels**: `gex:SPY`, `gex:QQQ`, `gex:IWM`
- **Output File**: `demo_greeks_YYYYMMDD_HHMMSS.txt`
- **Data**: Greeks exposure data for major ETFs

### Flow Alerts
- **Channel**: `flow-alerts`
- **Output File**: `demo_flowalerts_YYYYMMDD_HHMMSS.txt`
- **Data**: Unusual options flow alerts

## Customization

### Adding New Channels

Modify the `#subscribeToChannels()` method in `uw_websocket_client.js`:

```javascript
const channels = [
    { channel: 'option_trades:AAPL', msg_type: 'join' },  // Add Apple
    { channel: 'gex:SPY', msg_type: 'join' },
    // ... other channels
];
```

### Changing Configuration

Modify the `CONFIG` object at the top of the file:

```javascript
const CONFIG = {
    TIMEOUT_LENGTH: 30000,        // Message timeout (30 seconds)
    MAX_RECONNECT_ATTEMPTS: 5,    // Max reconnection attempts
    RECONNECT_DELAY: 5000,        // Initial reconnection delay
    FLUSH_INTERVAL: 1000,         // Data flush interval
    // ... other settings
};
```

## Output Files

The client creates timestamped files for each data type:

- `demo_optiontrades_20231215_143052.txt`
- `demo_greeks_20231215_143052.txt`
- `demo_flowalerts_20231215_143052.txt`

### File Format

Each line contains:
```
YYYY-MM-DD HH:MM:SS|channel_name|{"data":"object"}
```

Example:
```
2023-12-15 14:30:52|option_trades:TSLA|{"symbol":"TSLA","price":245.50,"volume":100}
```

## API Reference

### Events

The client emits the following events:

- `starting` - Client is starting up
- `connected` - Successfully connected to API
- `disconnected` - Connection lost
- `message` - New data message received
- `error` - Error occurred
- `shutdown` - Client is shutting down
- `log` - Log message generated

### Properties

- `client.isConnected` - Boolean indicating connection status
- `client.reconnectAttempt` - Current reconnection attempt number
- `client.bufferStats` - Object with buffer sizes for each channel

### Methods

- `client.start()` - Start the client and begin streaming
- `client.shutdown()` - Gracefully stop the client

## Error Handling

The client includes comprehensive error handling:

- **Connection Timeouts**: Automatic retry with exponential backoff
- **Network Errors**: Graceful reconnection with jitter to prevent storms
- **Data Errors**: Individual message parsing errors don't crash the client
- **File Errors**: Buffered writing with error recovery
