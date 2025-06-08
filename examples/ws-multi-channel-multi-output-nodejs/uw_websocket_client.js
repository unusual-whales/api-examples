/**
 * Unusual Whales WebSocket Client for Node.js
 * 
 * This client connects to the Unusual Whales API and streams real-time financial data.
 * It automatically handles reconnections, saves data to files, and manages connection health.
 * 
 * SETUP INSTRUCTIONS:
 * 1. Install dependencies: npm install ws dotenv
 * 2. Create a .env file with your API token: UW_TOKEN=your_token_here
 * 3. Run the client: node uw_websocket_client.js or npm run uw-client
 * 
 * WHAT THIS CLIENT DOES:
 * - Connects to Unusual Whales WebSocket API
 * - Subscribes to multiple data channels (option trades, Greeks, flow alerts)
 * - Saves incoming data to separate text files with timestamps
 * - Automatically reconnects if the connection drops
 * - Handles errors gracefully and logs all activity
 * 
 * FOR BEGINNERS:
 * - Lines starting with // are comments (explanatory text)
 * - const/let are ways to declare variables
 * - async/await are used for operations that take time (like network requests)
 * - Classes are blueprints for creating objects with methods and properties
 * - The # symbol makes properties private (only accessible within the class)
 */

// Import required Node.js modules
const WebSocket = require('ws');             // WebSocket library for real-time connections
const fs = require('fs').promises;           // File system module (promise-based for async operations)
const { EventEmitter } = require('events');  // EventEmitter for handling custom events
const { promisify } = require('util');       // Utility to convert callbacks to promises
require('dotenv').config();                  // Load environment variables from .env file

// Convert setTimeout to work with async/await
const sleep = promisify(setTimeout);

/**
 * Configuration object - all timing and connection settings in one place
 * Modify these values to change client behavior:
 * - TIMEOUT_LENGTH: How long to wait for messages before checking connection (30 seconds)
 * - MAX_RECONNECT_ATTEMPTS: How many times to try reconnecting (5 attempts)
 * - RECONNECT_DELAY: Starting delay between reconnection attempts (5 seconds)
 * - RECONNECT_DELAY_MAX: Maximum delay between reconnection attempts (60 seconds)
 * - FLUSH_INTERVAL: How often to save data to files (1 second)
 * - CONNECTION_TIMEOUT: How long to wait for initial connection (10 seconds)
 * - PING_TIMEOUT: How long to wait for ping response (10 seconds)
 */
const CONFIG = {
    TIMEOUT_LENGTH: 30000,        // 30 seconds in milliseconds
    MAX_RECONNECT_ATTEMPTS: 5,    // Maximum reconnection attempts
    RECONNECT_DELAY: 5000,        // 5 seconds in milliseconds
    RECONNECT_DELAY_MAX: 60000,   // 60 seconds in milliseconds
    FLUSH_INTERVAL: 1000,         // 1 second flush interval
    CONNECTION_TIMEOUT: 10000,    // 10 seconds in milliseconds
    PING_TIMEOUT: 10000           // 10 seconds in milliseconds
};

/**
 * Custom error class for connection timeouts
 * This helps us identify when connections fail due to timeout vs other reasons
 */
class ConnectionTimeoutError extends Error {
    constructor(message = 'Connection timeout') {
        super(message);
        this.name = 'ConnectionTimeoutError';
    }
}

/**
 * Custom error class for when we've tried reconnecting too many times
 * This helps us know when to give up trying to reconnect
 */
class MaxReconnectAttemptsError extends Error {
    constructor(attempts) {
        super(`Maximum reconnection attempts (${attempts}) reached`);
        this.name = 'MaxReconnectAttemptsError';
    }
}

/**
 * Main WebSocket client class
 * Extends EventEmitter so we can emit custom events (connected, disconnected, etc.)
 * 
 * ARCHITECTURE OVERVIEW:
 * - This class manages the WebSocket connection to Unusual Whales
 * - It buffers incoming messages and writes them to files every second
 * - It automatically reconnects with exponential backoff if connection drops
 * - It monitors connection health with ping/pong messages
 * - It handles graceful shutdown when the program is terminated
 */
class UnusualWhalesClient extends EventEmitter {
    // Private fields (# makes them private - only accessible within this class)
    #reconnectAttempt = 0;         // Current reconnection attempt number
    #running = true;               // Whether the client should keep running
    #ws = null;                    // The WebSocket connection object
    #lastFlushTime = Date.now();   // When we last saved data to files
    #lastMessageTime = Date.now(); // When we last received a message (for timeout detection)
    
    // Map to store message buffers for each data type
    // Using Map instead of object for better performance and cleaner code
    #messageBuffers = new Map([
        ['optiontrades', []],     // Buffer for option trade messages
        ['greeks', []],           // Buffer for Greek exposure data
        ['flowalerts', []]        // Buffer for flow alert messages
    ]);
    
    #filenames = new Map();      // Map to store filename for each data type
    #flushTimer = null;          // Timer for periodic data flushing
    #timeoutTimer = null;        // Timer for connection timeout monitoring

    /**
     * Constructor - runs when you create a new UnusualWhalesClient instance
     * Sets up the client by preparing files, signal handlers, and timers
     */
    constructor() {
        super(); // Call parent EventEmitter constructor
        this.#setupFiles();          // Create timestamped filenames
        this.#setupSignalHandlers(); // Handle Ctrl+C and other shutdown signals
        this.#setupFlushTimer();     // Start timer to save data every second
    }

    /**
     * Creates unique filenames with timestamps for each data type
     * Example: demo_optiontrades_20231215_143052.txt
     * This ensures each run creates new files and doesn't overwrite old data
     */
    #setupFiles() {
        // Create timestamp string: YYYYMMDD_HHMMSS format
        const timestamp = new Date().toISOString()
            .replace(/[-:]/g, '')     // Remove dashes and colons
            .replace(/\..+/, '')      // Remove milliseconds and timezone
            .replace('T', '_');       // Replace T with underscore
        
        // Set filenames for each data type
        this.#filenames.set('optiontrades', `demo_optiontrades_${timestamp}.txt`);
        this.#filenames.set('greeks', `demo_greeks_${timestamp}.txt`);
        this.#filenames.set('flowalerts', `demo_flowalerts_${timestamp}.txt`);
    }

    /**
     * Sets up handlers for system signals (Ctrl+C, kill commands)
     * This ensures we save any remaining data before the program exits
     */
    #setupSignalHandlers() {
        const handleShutdown = (signal) => {
            this.#log(`Gracefully shutting down on ${signal}`);
            this.shutdown(); // Call our cleanup method
        };

        // Listen for common termination signals
        // 'once' means the handler will only run one time
        process.once('SIGINT', () => handleShutdown('SIGINT'));   // Ctrl+C
        process.once('SIGTERM', () => handleShutdown('SIGTERM')); // Kill command
    }

    /**
     * Sets up a timer that saves buffered data to files every second
     * This ensures we don't lose data if the program crashes
     */
    #setupFlushTimer() {
        this.#flushTimer = setInterval(async () => {
            await this.#flushBuffers(); // Save all buffered data to files
        }, CONFIG.FLUSH_INTERVAL);
    }

    /**
     * Logging method - formats and outputs messages with timestamps
     * Also emits log events so external code can capture logs
     * 
     * @param {string} message - The message to log
     * @param {string} level - Log level: 'info', 'warning', 'error'
     */
    #log(message, level = 'info') {
        // Create formatted timestamp and message
        const timestamp = new Date().toISOString().replace('T', ' ').replace('Z', '');
        const formattedMessage = `${timestamp}|uw_client|${level.toUpperCase()}|${message}`;
        console.log(formattedMessage);
        
        // Emit log event so external code can capture logs
        this.emit('log', { message, level, timestamp });
    }

    /**
     * Helper method to get current date/time as a formatted string
     * Used for timestamping data messages
     * 
     * @returns {string} Current date/time in YYYY-MM-DD HH:MM:SS format
     */
    #getCurrentDateTime() {
        return new Date().toISOString().replace('T', ' ').replace('Z', '');
    }

    /**
     * Saves all buffered messages to their respective files
     * Uses Promise.allSettled to save all files in parallel for better performance
     * This method is called every second by the flush timer
     */
    async #flushBuffers() {
        // Create array of promises to save each buffer that has data
        const flushPromises = Array.from(this.#messageBuffers.entries())
            .filter(([, buffer]) => buffer.length > 0) // Only process buffers with data
            .map(async ([channel, buffer]) => {
                try {
                    const filename = this.#filenames.get(channel);
                    const content = buffer.join(''); // Combine all messages into one string
                    await fs.appendFile(filename, content); // Save to file
                    this.#messageBuffers.set(channel, []); // Clear the buffer
                } catch (error) {
                    this.#log(`Error flushing ${channel} buffer: ${error.message}`, 'error');
                }
            });

        // Wait for all file operations to complete (or fail)
        await Promise.allSettled(flushPromises);
    }

    /**
     * Establishes WebSocket connection to Unusual Whales API
     * Includes timeout handling and proper cleanup
     * 
     * @returns {Promise} Resolves when connected, rejects on error/timeout
     */
    async #connect() {
        // Get API token from environment variables (.env file)
        const uwApiToken = process.env.UW_TOKEN;
        if (!uwApiToken) {
            throw new Error('UW_TOKEN environment variable is required');
        }

        // Build WebSocket URL with authentication token
        const uri = `wss://api.unusualwhales.com/socket?token=${uwApiToken}`;
        
        return new Promise((resolve, reject) => {
            // Create new WebSocket connection
            this.#ws = new WebSocket(uri);
            
            // Set up timeout to prevent hanging forever
            const connectionTimeout = setTimeout(() => {
                this.#ws?.terminate(); // Force close the connection
                reject(new ConnectionTimeoutError());
            }, CONFIG.CONNECTION_TIMEOUT);

            // Helper function to clean up event listeners and timers
            const cleanup = () => {
                clearTimeout(connectionTimeout);
                this.#ws?.removeAllListeners(); // Remove temporary listeners
            };

            // Handle successful connection
            this.#ws.once('open', () => {
                cleanup();
                this.#log('WebSocket connection established');
                this.#setupWebSocketListeners(); // Set up permanent event listeners
                this.#subscribeToChannels();     // Subscribe to data channels
                this.#startTimeoutMonitoring();  // Start monitoring for connection health
                resolve(); // Connection successful
            });

            // Handle connection errors
            this.#ws.once('error', (error) => {
                cleanup();
                this.#log(`WebSocket connection error: ${error.message}`, 'error');
                reject(error);
            });
        });
    }

    /**
     * Sets up permanent event listeners for the WebSocket connection
     * These listeners handle incoming messages, disconnections, and errors
     */
    #setupWebSocketListeners() {
        // Handle incoming data messages
        this.#ws.on('message', (data) => this.#handleMessage(data));
        
        // Handle connection closing
        this.#ws.on('close', (code, reason) => {
            const reasonStr = reason?.toString() || 'Unknown reason';
            this.#log(`WebSocket connection closed: ${code} - ${reasonStr}`, 'warning');
            this.#stopTimeoutMonitoring(); // Stop health monitoring
            this.emit('disconnected', { code, reason: reasonStr }); // Notify external code
        });

        // Handle WebSocket errors
        this.#ws.on('error', (error) => {
            this.#log(`WebSocket error: ${error.message}`, 'error');
            this.emit('error', error); // Notify external code
        });

        // Handle pong responses (for connection health checks)
        this.#ws.on('pong', () => {
            this.#log('Received pong - connection is alive');
            this.#lastMessageTime = Date.now(); // Update last activity time
        });
    }

    /**
     * Subscribes to Unusual Whales data channels
     * You can modify this list to subscribe to different channels
     * Available channels include option_trades, gex (Greeks), flow-alerts, etc.
     */
    #subscribeToChannels() {
        // Define channels to subscribe to
        // You can add/remove channels here based on what data you want
        const channels = [
            { channel: 'option_trades:TSLA', msg_type: 'join' },  // Tesla option trades
            { channel: 'gex:SPY', msg_type: 'join' },             // SPY Greeks exposure
            { channel: 'gex:QQQ', msg_type: 'join' },             // QQQ Greeks exposure
            { channel: 'gex:IWM', msg_type: 'join' },             // IWM Greeks exposure
            { channel: 'flow-alerts', msg_type: 'join' }          // Flow alerts
        ];

        // Send subscription message for each channel
        for (const msg of channels) {
            if (this.#ws?.readyState === WebSocket.OPEN) {
                this.#ws.send(JSON.stringify(msg)); // Send as JSON string
                this.#log(`Subscribed to ${msg.channel} channel`);
            }
        }
    }

    /**
     * Processes incoming WebSocket messages
     * Parses the data, routes it to appropriate buffer, and triggers events
     * 
     * @param {Buffer|string} data - Raw message data from WebSocket
     */
    #handleMessage(data) {
        try {
            // Update last message time for timeout monitoring
            this.#lastMessageTime = Date.now();
            
            // Parse JSON message - format is usually [channel, payload]
            const message = JSON.parse(data.toString());
            const [channel, payload] = message;
            
            // Format message with timestamp for file storage
            const formattedMessage = `${this.#getCurrentDateTime()}|${channel}|${JSON.stringify(payload)}\n`;
            
            // Route message to appropriate buffer based on channel name
            const bufferKey = this.#getBufferKey(channel);
            if (bufferKey) {
                this.#messageBuffers.get(bufferKey).push(formattedMessage);
                // Emit event so external code can process messages in real-time
                this.emit('message', { channel, payload, bufferKey });
            } else {
                this.#log(`Unknown channel: ${channel}`, 'error');
            }

        } catch (error) {
            this.#log(`Error parsing message: ${error.message}`, 'error');
        }
    }

    /**
     * Determines which buffer to use based on channel name
     * This routing logic determines how messages are categorized and saved
     * 
     * @param {string} channel - Channel name from the message
     * @returns {string|null} Buffer key or null if channel is unknown
     */
    #getBufferKey(channel) {
        // Route based on channel name patterns
        if (channel.includes('option_trades')) return 'optiontrades';
        if (channel.includes('flow-alerts')) return 'flowalerts';
        if (channel.includes('gex')) return 'greeks';
        return null; // Unknown channel
    }

    /**
     * Starts monitoring connection health
     * Checks if we've received messages recently, pings server if not
     * Runs every 5 seconds to check for timeouts
     */
    #startTimeoutMonitoring() {
        this.#timeoutTimer = setInterval(async () => {
            const timeSinceLastMessage = Date.now() - this.#lastMessageTime;
            
            // Check if we haven't received messages for too long
            if (timeSinceLastMessage >= CONFIG.TIMEOUT_LENGTH) {
                this.#log(`No messages received for ${CONFIG.TIMEOUT_LENGTH/1000}s, checking connection...`);
                
                // Send ping to check if connection is still alive
                const isAlive = await this.#checkConnection();
                if (!isAlive) {
                    this.#log('Connection appears to be dead', 'warning');
                    this.#ws?.terminate(); // Force close dead connection
                } else {
                    this.#lastMessageTime = Date.now(); // Reset timer if connection is good
                }
            }
        }, 5000); // Check every 5 seconds
    }

    /**
     * Stops the timeout monitoring timer
     * Called when connection closes or during shutdown
     */
    #stopTimeoutMonitoring() {
        if (this.#timeoutTimer) {
            clearInterval(this.#timeoutTimer);
            this.#timeoutTimer = null;
        }
    }

    /**
     * Checks if WebSocket connection is still alive by sending a ping
     * Returns true if we get a pong response, false otherwise
     * 
     * @returns {Promise<boolean>} True if connection is alive, false if dead
     */
    async #checkConnection() {
        // Check if WebSocket is in OPEN state
        if (this.#ws?.readyState !== WebSocket.OPEN) {
            return false;
        }

        return new Promise((resolve) => {
            // Set timeout for ping response
            const timeout = setTimeout(() => resolve(false), CONFIG.PING_TIMEOUT);

            // Helper to clean up event listeners
            const cleanup = () => {
                clearTimeout(timeout);
                this.#ws?.off('pong', handlePong);
                this.#ws?.off('error', handleError);
            };

            // Handle successful pong response
            const handlePong = () => {
                cleanup();
                resolve(true); // Connection is alive
            };

            // Handle ping error
            const handleError = () => {
                cleanup();
                resolve(false); // Connection is dead
            };

            // Set up one-time listeners and send ping
            this.#ws.once('pong', handlePong);
            this.#ws.once('error', handleError);
            this.#ws.ping(); // Send ping message
        });
    }

    /**
     * Calculates delay for next reconnection attempt using exponential backoff
     * Delay increases with each attempt: 5s, 10s, 20s, 40s, 60s (max)
     * Adds random jitter to prevent multiple clients reconnecting simultaneously
     * 
     * @returns {number} Delay in milliseconds
     */
    #calculateReconnectDelay() {
        // Calculate exponential backoff: delay * 2^(attempt-1)
        const delay = Math.min(
            CONFIG.RECONNECT_DELAY * (2 ** (this.#reconnectAttempt - 1)),
            CONFIG.RECONNECT_DELAY_MAX
        );
        
        // Add random jitter (0-10% of delay) to avoid reconnection storms
        const jitter = delay * 0.1 * Math.random();
        return delay + jitter;
    }

    /**
     * Main method to start the WebSocket client
     * Handles connection, reconnection logic, and error recovery
     * This is the primary method you call to start streaming data
     */
    async start() {
        this.#log('Starting Unusual Whales WebSocket client...');
        this.emit('starting'); // Notify external code that we're starting
        
        // Main reconnection loop
        while (this.#running && this.#reconnectAttempt <= CONFIG.MAX_RECONNECT_ATTEMPTS) {
            try {
                // Wait before reconnecting (except for first attempt)
                if (this.#reconnectAttempt > 0) {
                    const reconnectDelay = this.#calculateReconnectDelay();
                    this.#log(`Reconnection attempt ${this.#reconnectAttempt} of ${CONFIG.MAX_RECONNECT_ATTEMPTS} after waiting ${(reconnectDelay/1000).toFixed(2)} seconds...`);
                    await sleep(reconnectDelay); // Wait before retrying
                }

                // Attempt to connect
                await this.#connect();
                this.#reconnectAttempt = 0; // Reset counter on successful connection
                this.emit('connected'); // Notify external code of successful connection
                
                // Wait for disconnection (this promise resolves when connection closes)
                await new Promise((resolve, reject) => {
                    const handleDisconnect = () => {
                        this.off('disconnected', handleDisconnect);
                        resolve(); // Connection closed, proceed to reconnect
                    };

                    const handleError = (error) => {
                        this.off('error', handleError);
                        this.off('disconnected', handleDisconnect);
                        reject(error); // Error occurred, handle in catch block
                    };

                    // Set up one-time listeners for connection events
                    this.once('disconnected', handleDisconnect);
                    this.once('error', handleError);
                });
                
                // Check if shutdown was requested
                if (!this.#running) {
                    this.#log('WebSocket connection closed normally');
                    break; // Exit reconnection loop
                }
                
            } catch (error) {
                this.#log(`Connection error: ${error.message}`, 'error');
                
                // Clean up on error
                await this.#flushBuffers();     // Save any remaining data
                this.#stopTimeoutMonitoring();  // Stop monitoring
                
                // Close and cleanup WebSocket
                if (this.#ws) {
                    this.#ws.terminate();
                    this.#ws = null;
                }
                
                this.#reconnectAttempt++; // Increment retry counter
                
                // Check if we've exceeded max attempts
                if (this.#reconnectAttempt > CONFIG.MAX_RECONNECT_ATTEMPTS) {
                    throw new MaxReconnectAttemptsError(CONFIG.MAX_RECONNECT_ATTEMPTS);
                }
            }
        }
        
        await this.#cleanup(); // Final cleanup
    }

    /**
     * Gracefully shuts down the client
     * Saves any remaining data and cleans up resources
     * Call this method when you want to stop the client
     */
    async shutdown() {
        this.#log('Shutdown requested');
        this.#running = false; // Signal main loop to stop
        
        // Stop all timers
        this.#stopTimeoutMonitoring();
        
        if (this.#flushTimer) {
            clearInterval(this.#flushTimer);
            this.#flushTimer = null;
        }
        
        // Close WebSocket connection
        if (this.#ws) {
            this.#ws.terminate();
            this.#ws = null;
        }
        
        await this.#cleanup();     // Final cleanup
        this.emit('shutdown');     // Notify external code
        process.exit(0);           // Exit the program
    }

    /**
     * Performs final cleanup operations
     * Saves any remaining buffered data and removes event listeners
     */
    async #cleanup() {
        this.#log('Cleaning up...');
        
        await this.#flushBuffers();    // Save any remaining data
        this.removeAllListeners();     // Remove all event listeners
        
        this.#log('Cleanup complete');
    }

    // ========================================
    // PUBLIC GETTERS - Methods for monitoring the client externally
    // ========================================

    /**
     * Check if currently connected to WebSocket
     * @returns {boolean} True if connected, false otherwise
     */
    get isConnected() {
        return this.#ws?.readyState === WebSocket.OPEN;
    }

    /**
     * Get current reconnection attempt number
     * @returns {number} Current reconnection attempt (0 = first connection)
     */
    get reconnectAttempt() {
        return this.#reconnectAttempt;
    }

    /**
     * Get statistics about message buffers
     * @returns {Object} Object with buffer sizes for each channel
     */
    get bufferStats() {
        const stats = {};
        for (const [key, buffer] of this.#messageBuffers) {
            stats[key] = buffer.length;
        }
        return stats;
    }
}

// ========================================
// MAIN EXECUTION SECTION
// ========================================

/**
 * This section runs when the file is executed directly (not imported as a module)
 * It creates a client instance and starts the connection process
 */
if (require.main === module) {
    // Create new client instance
    const client = new UnusualWhalesClient();
    
    // Set up event listeners for monitoring (optional)
    // You can modify or remove these based on your needs
    client.on('connected', () => console.log('Connected to Unusual Whales'));
    client.on('disconnected', () => console.log('Disconnected from Unusual Whales'));
    client.on('message', (data) => {
        // Optional: Log message counts or process messages in real-time
        // Uncomment the line below to see every message received
        // console.log(`Received message on ${data.channel} (buffer: ${data.bufferKey})`);
    });
    
    // Start the client and handle any fatal errors
    client.start().catch(error => {
        console.error('Fatal error:', error.message);
        process.exit(1); // Exit with error code
    });
}

// Export the class so it can be imported and used in other files
module.exports = UnusualWhalesClient;