# Unusual Whales API Examples
A collection of heavily-commented sample scripts and notebooks demonstrating how to use the Unusual Whales API.

## Unusual Whales Links
- Docs: [https://api.unusualwhales.com/docs#/](https://api.unusualwhales.com/docs#/)
- Pricing: [https://unusualwhales.com/public-api#pricing](https://unusualwhales.com/public-api#pricing)
- How To Check Your API Usage: [https://unusualwhales.com/information/how-to-check-your-api-usage](https://unusualwhales.com/information/how-to-check-your-api-usage)
- **For users of LLM tools like ChatGPT, Claude, Gemini, etc.** How To Fix 404 Errors: [https://unusualwhales.com/information/how-to-fix-404-errors-when-using-ai-tools-with-the-unusual-whales-api](https://unusualwhales.com/information/how-to-fix-404-errors-when-using-ai-tools-with-the-unusual-whales-api)

## Examples

### Websocket: How to stream data from multiple channel and write to multiple outputs
- `examples/ws-multi-channel-multi-output`
- This script connects to several different websocket channels (greeks, flow alerts, and all option trades for ticker `TSLA`). It writes results to multiple buffers and flushes those buffers to multiple files once per second. The folder contains example output files as well.
