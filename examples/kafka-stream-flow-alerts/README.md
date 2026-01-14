# Stream Flow Alerts via Kafka Consumer
This python script demonstrates how to set up your environment then stream Flow Alerts from the `flow-alerts` Kafka topic.

## Notes
- The file `sample_flow_alerts_from_stream.txt` contains a few Flow Alert records for easy schema reference

## Step-by-Step Guide
Clone, fork-and-clone, or download the entire repo as a zip file from the green "Code" button dropdown: [https://github.com/unusual-whales/api-examples](https://github.com/unusual-whales/api-examples). Once you have the repo, navigate into the `api-examples/examples/kafka-stream-flow-alerts` directory and follow these instructions. (For reference, these steps were executed on an Ubuntu instance running on Windows WSL2.)

1. Create a virtual environment using `venv`
```
$ python3 -m venv .venv
```

2. Activate the virtual environment
```
$ source .venv/bin/activate
```

3. Install the required packages
```
$ pip install -r requirements.txt
```

4. Update the consumer.py file with your `topic`, `group_id`, `username`, and `password`
In the main function of the `consumer.py` file, the following variables need to be set:

```python
def main():
    # Configuration
    BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP', 'stream.unusualwhales.com:9095')
    TOPIC = os.getenv('KAFKA_TOPIC', 'your-topic-name')
    GROUP_ID = os.getenv('KAFKA_GROUP_ID', f'python-consumer-{os.getpid()}')  # Unique group per process
    USERNAME = os.getenv('KAFKA_USERNAME', 'your-username')
    PASSWORD = os.getenv('KAFKA_PASSWORD', 'your-password')
```

Either (a) update the fallback values in `consumer.py` like this:

```python
def main():
    # Configuration
    BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP', 'stream.unusualwhales.com:9095')
    TOPIC = os.getenv('KAFKA_TOPIC', 'flow-alerts')
    GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'the-group-id-dan-sent-you')  # Unique group per process
    USERNAME = os.getenv('KAFKA_USERNAME', 'the-username-dan-sent-you')
    PASSWORD = os.getenv('KAFKA_PASSWORD', 'the-password-dan-sent-you')
```

Or (b) create environment variables `KAFKA_TOPIC`, `KAFKA_GROUP_ID`, `KAFKA_USERNAME`, and `KAFKA_PASSWORD` in your `~/.bashrc` then source it before moving on to the next step:

```
$ vim ~/.bashrc
```

```shell
# ... adding these variables to the end of the .bashrc file
# ...
# ...
export UW_KAFKA_TOPIC="flow-alerts"
export UW_KAFKA_GROUP_ID="the-group-id-dan-sent-you"
export UW_KAFKA_USERNAME="the-username-dan-sent-you"
export UW_KAFKA_PASSWORD="the-password-dan-sent-you"
```

```
$ source ~/.bashrc
```

5. Run the `gen_protos.sh` script to generate the python protobuf files

```
$ chmod +x gen_protos.sh
$ ./gen_protos.sh
```

After executing that file, you will see many new python files in the `protos_gen/client/` directory:

```
$ cd protos_gen/client
$ ls -lGh

total 48K
-rw-r--r-- 1 danwagnerco    0 Jan 13 17:29 __init__.py
drwxr-xr-x 2 danwagnerco 4.0K Jan 13 15:41 __pycache__
-rw-r--r-- 1 danwagnerco 1.4K Jan 13 17:29 announce_time_client_pb2.py
-rw-r--r-- 1 danwagnerco 1.3K Jan 13 17:29 date_client_pb2.py
-rw-r--r-- 1 danwagnerco 1.4K Jan 13 17:29 decimal_client_pb2.py
-rw-r--r-- 1 danwagnerco 2.7K Jan 13 17:29 flow_alert_client_pb2.py
-rw-r--r-- 1 danwagnerco 1.6K Jan 13 17:29 issue_type_client_pb2.py
-rw-r--r-- 1 danwagnerco 3.0K Jan 13 17:29 option_state_client_pb2.py
-rw-r--r-- 1 danwagnerco 2.6K Jan 13 17:29 options_client_pb2.py
-rw-r--r-- 1 danwagnerco 1.6K Jan 13 17:29 sector_client_pb2.py
-rw-r--r-- 1 danwagnerco 3.0K Jan 13 17:29 ticker_info_client_pb2.py
-rw-r--r-- 1 danwagnerco 4.2K Jan 13 17:29 trade_report_client_pb2.py
```

You are now ready to run the `consumer.py` script!

6. Run the `consumer.py` script

```
$ python consumer.py
Connecting to stream.unusualwhales.com:9095 (topic: flow-alerts)

Starting to consume messages... (Ctrl+C to stop)

# Flurry of incoming messages, for example:

Key: flow-alert
Decoded Message:
{
  "rule_id": "e6b9f0b6-fcd9-44fe-9d1c-f53521c152c3",
  "ticker": "SLV",
  "option_chain": "SLV260206C00077000",
  "underlying_price": 70.215,
  "volume": "201",
  "total_size": 120,
  "total_premium": 39000.0,
  "total_ask_side_prem": 39000.0,
  "start_time": "1767799954951",
  "end_time": "1767799954952",
  "price": 3.25,
  "open_interest": 507,
  "id": "47750cfd-5cd9-4950-b6e7-85724d84c41e",
  "has_singleleg": true,
  "volume_oi_ratio": 0.39644970414201186,
  "trade_ids": [
    "8f7785e8-dac9-4e85-89ad-39d4bdc33b5c",
    "9f8ce0ad-489a-43d5-adcd-446587d02ee7",
    "4368a1bb-afba-4717-b5da-474f0e31beba",
    "bd5c0cdb-35d6-40fb-ac19-bc35e6d45dc8",
    "e362de79-c1a7-4ad3-b04e-70c314e41c9f",
    "8c365ff8-ce54-4265-986d-efb825b92635",
    "752d06ba-8ce8-4aca-9148-74c55db5a4f0"
  ],
  "trade_count": 7,
  "expiry_count": 1,
  "executed_at": "1767799954952",
  "ask_vol": "130",
  "bid_vol": "37",
  "mid_vol": "34",
  "multi_vol": "14",
  "upstream_condition_details": [
    "auto"
  ],
  "exchanges": [
    "SPHR",
    "EDGO",
    "XBXO",
    "MCRY",
    "AMXO"
  ],
  "bid": "3.2",
  "ask": "3.25"
}
```
