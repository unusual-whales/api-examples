import os
import httpx
from pathlib import Path
import polars as pl

# Interact with API
uw_token = os.getenv('UW_TOKEN')
headers = {
    'Authorization': uw_token,
    'Accept': 'application/json, text/plain',
}

# Get custom alert configurations
url = 'https://api.unusualwhales.com/api/alerts/configuration'
rsp = httpx.get(url, headers=headers)

# >>> rsp.status_code
# 200
# >>> rsp.json()['data']
# [{'id': '329de3cd-c5ae-45a7-926d-3409516fffa7',
#   'name': 'OS Bearish Credit Trades',
#   'status': 'active',
#   'config': {'issue_types': ['Common Stock', 'ETF', 'ADR'],
#    'max_dte': 60,
#    'max_multileg_volume_ratio': 0.1,
#    'min_bid_perc': 0.8,
#    'min_diff': '-0.1',
#    'min_dte': 1,
#    'min_premium': 100000,
#    'symbols': 'all',
#    'type': 'call',
#    'vol_greater_oi': True},
#   'description': None,
#   'created_at': '2025-05-30T19:01:11Z',
#   'noti_type': 'option_contract',
#   'mobile_only': False},
#  {'id': 'ad7ad6e9-2480-4587-81b3-02ef53302b23',
#   'name': 'OS Bullish Credit Trades',
#   'status': 'active',
#   'config': {'issue_types': ['Common Stock', 'ETF', 'ADR'],
#    'max_dte': 60,
#    'max_multileg_volume_ratio': 0.1,
#    'min_bid_perc': 0.8,
#    'min_diff': '-0.1',
#    'min_premium': 100000,
#    'symbols': 'all',
#    'type': 'put',
#    'vol_greater_oi': True},
#   'description': None,
#   'created_at': '2025-05-30T19:00:49Z',
#   'noti_type': 'option_contract',
#   'mobile_only': False},
#    ...

# Before creating the new custom alert, get the existing config names and IDs:
# >>> configs = {d['name']: d['id'] for d in rsp.json()['data']}
# >>> configs
# {'OS Bearish Credit Trades': '329de3cd-c5ae-45a7-926d-3409516fffa7',
#  'OS Bullish Credit Trades': 'ad7ad6e9-2480-4587-81b3-02ef53302b23',
#  'OS Cheap Calls': '5a738333-2559-4a24-91ae-1627047435ac',
#  'OS Put Sells': 'd15fa1ad-2d87-485a-bec3-4f18f7effa5d',
#  'OS Long-Term Calls': '5cd91d65-2926-4478-bb30-6897c41255dc',
#  'OS Deep Conviction Puts': 'bba3eb10-5e40-46f4-8a41-802ed6f15f39',
#  'OS Deep Conviction Calls': '6e3bfab1-244f-40b5-b2b1-8e9aa036a0cf',
#  'OS Unusually Bullish': '8b837eb2-8b93-4793-a404-37024349c0e8',
#  'Insider Sell Cluster': 'f74029af-a6ff-4121-876f-226c99898d64',
#  'Insider Buy Cluster': '15b4c203-ba69-4edb-af44-8c71fa04c173',
#  'coolguy5255 flow': '114dce32-6b83-4721-9fbd-d1fe1ad53e3c',
#  'Analyst Initiate Buy 3X With 20pct Upside': '582e901b-a3bf-4857-8a9e-4c9bef9e1b24',
#  'Market Tide Crossover': 'cc743251-0636-4d78-91db-f302df1e6ac5',
#  '250K Put Seller Stock or ETF': '9657ed04-81c4-4bfe-8a46-47013b3c4356',
#  'Analyst Buy Cluster': 'ef5084a7-ed5f-41a6-8796-0ac8b23d3e1a',
#  '50K Call Buyer Cheap Convexity Stock Only': 'b6ebbe78-f141-4bcc-946e-69e2bf80c45b',
#  '500K ITM Call Buyer Stock Only': 'c90e570d-07b3-455e-b833-d7f1fe5c6995',
#  '500K OTM Call Buyer Stock Only': 'a98f6c2b-25b6-4b60-a42f-e92aa9d77690',
#  '1M 6mo Call Buyer Stock or ETF': '7c4e68e0-8401-40b2-bbaf-06ca3da551b6',
#  '250K Put Buy Confident Delta Stock Only': 'eb80b55d-ece2-443d-a202-176b1a21f51b',
#  '3X over 30d avg option volume Call emphasis $100K': 'ec5bb6b0-6f21-4311-bcca-54b1314eeb93',
#  'Low Volume 3x Avg 10K Bets': '2bb448e5-ed87-4015-9ec8-def1d7fff30a'}

# Then after saving the Nicholas Stonerman Interval Flow config as a custom alert
# on the Unusual Whales web platform, you can retrive the updated list of configs:
# >>> url = 'https://api.unusualwhales.com/api/alerts/configuration'
# >>> rsp = httpx.get(url, headers=headers)
# >>> configs = {d['name']: d['id'] for d in rsp.json()['data']}
# >>> configs
# {'Nicholas Stonerman': 'c07bd05a-f327-45a2-b71e-4b5aeb6edcc7',  # <- new config!
#  'OS Bearish Credit Trades': '329de3cd-c5ae-45a7-926d-3409516fffa7',
#  'OS Bullish Credit Trades': 'ad7ad6e9-2480-4587-81b3-02ef53302b23',
#  'OS Cheap Calls': '5a738333-2559-4a24-91ae-1627047435ac',
#  'OS Put Sells': 'd15fa1ad-2d87-485a-bec3-4f18f7effa5d',
#  'OS Long-Term Calls': '5cd91d65-2926-4478-bb30-6897c41255dc',
#  'OS Deep Conviction Puts': 'bba3eb10-5e40-46f4-8a41-802ed6f15f39',
#  'OS Deep Conviction Calls': '6e3bfab1-244f-40b5-b2b1-8e9aa036a0cf',
#  'OS Unusually Bullish': '8b837eb2-8b93-4793-a404-37024349c0e8',
#  'Insider Sell Cluster': 'f74029af-a6ff-4121-876f-226c99898d64',
#  'Insider Buy Cluster': '15b4c203-ba69-4edb-af44-8c71fa04c173',
#  'coolguy5255 flow': '114dce32-6b83-4721-9fbd-d1fe1ad53e3c',
#  'Analyst Initiate Buy 3X With 20pct Upside': '582e901b-a3bf-4857-8a9e-4c9bef9e1b24',
#  'Market Tide Crossover': 'cc743251-0636-4d78-91db-f302df1e6ac5',
#  '250K Put Seller Stock or ETF': '9657ed04-81c4-4bfe-8a46-47013b3c4356',
#  'Analyst Buy Cluster': 'ef5084a7-ed5f-41a6-8796-0ac8b23d3e1a',
#  '50K Call Buyer Cheap Convexity Stock Only': 'b6ebbe78-f141-4bcc-946e-69e2bf80c45b',
#  '500K ITM Call Buyer Stock Only': 'c90e570d-07b3-455e-b833-d7f1fe5c6995',
#  '500K OTM Call Buyer Stock Only': 'a98f6c2b-25b6-4b60-a42f-e92aa9d77690',
#  '1M 6mo Call Buyer Stock or ETF': '7c4e68e0-8401-40b2-bbaf-06ca3da551b6',
#  '250K Put Buy Confident Delta Stock Only': 'eb80b55d-ece2-443d-a202-176b1a21f51b',
#  '3X over 30d avg option volume Call emphasis $100K': 'ec5bb6b0-6f21-4311-bcca-54b1314eeb93',
#  'Low Volume 3x Avg 10K Bets': '2bb448e5-ed87-4015-9ec8-def1d7fff30a'}

# Now that we have the config ID for the Nicholas Stonerman Interval Flow alert,
# we can retrieve the alerts for that config:
url = 'https://api.unusualwhales.com/api/alerts'
config_ids = ['c07bd05a-f327-45a2-b71e-4b5aeb6edcc7']
params = {
    'config_ids[]': config_ids,
    'limit': 200,
}
rsp = httpx.get(url, headers=headers, params=params)
# >>> rsp.json()['data']
# [{'id': 'dfb52150-d033-4fb8-8ee2-bd0a8952692e',
#   'meta': {'ask_volume': 1000,
#    'avg_fill': '0.7000',
#    'bid_volume': 0,
#    'close': '0.70',
#    'diff': '0.0728',
#    'iv_change': '-0.0026',
#    'minute': 10,
#    'multi_leg_vol_ratio': '0',
#    'open_interest': 273,
#    'rounded_tape_time': 1749496200000,
#    'total_premium': '70000',
#    'underlying_symbol': 'AI',
#    'vol_oi_ratio': '3.6630',
#    'volume': 1000},
#   'name': 'Nicholas Stonerman',
#   'symbol': 'AI250703C00028000',
#   'created_at': '2025-06-09T19:18:54Z',
#   'tape_time': '2025-06-09T19:18:52Z',
#   'user_noti_config_id': 'c07bd05a-f327-45a2-b71e-4b5aeb6edcc7',
#   'noti_type': 'option_contract_interval',
#   'symbol_type': 'option_chain'},
#  {'id': 'f8b9f3be-31b4-48a3-857e-e90086a6ee4a',
#   'meta': {'ask_volume': 463,
#    'avg_fill': '10.9700',
#    'bid_volume': 35,
#    'close': '11.00',
#    'diff': '0.0075',
#    'iv_change': '0.0010',
#    'minute': 10,
#    'multi_leg_vol_ratio': '0',
#    'open_interest': 46,
#    'rounded_tape_time': 1749496200000,
#    'total_premium': '559472',
#    'underlying_symbol': 'LEN',
#    'vol_oi_ratio': '11.0870',
#    'volume': 510},
#   'name': 'Nicholas Stonerman',
#   'symbol': 'LEN251219P00110000',
#   'created_at': '2025-06-09T19:18:49Z',
#   'tape_time': '2025-06-09T19:18:49Z',
#   'user_noti_config_id': 'c07bd05a-f327-45a2-b71e-4b5aeb6edcc7',
#   'noti_type': 'option_contract_interval',
#   'symbol_type': 'option_chain'},
#   ...

# Combine the alerts into a DataFrame
alerts = []
for alert in rsp.json()['data']:
    d = {}
    d['id'] = alert['id']
    d['name'] = alert['name']
    d['symbol'] = alert['symbol']
    d['created_at'] = alert['created_at']
    d['tape_time'] = alert['tape_time']
    d['user_noti_config_id'] = alert['user_noti_config_id']
    d['noti_type'] = alert['noti_type']
    d['symbol_type'] = alert['symbol_type']
    d['ask_volume'] = alert['meta']['ask_volume']
    d['avg_fill'] = alert['meta']['avg_fill']
    d['bid_volume'] = alert['meta']['bid_volume']
    d['close'] = alert['meta']['close']
    d['diff'] = alert['meta']['diff']
    d['iv_change'] = alert['meta']['iv_change']
    d['minute'] = alert['meta']['minute']
    d['multi_leg_vol_ratio'] = alert['meta']['multi_leg_vol_ratio']
    d['open_interest'] = alert['meta']['open_interest']
    d['rounded_tape_time'] = alert['meta']['rounded_tape_time']
    d['total_premium'] = alert['meta']['total_premium']
    d['underlying_symbol'] = alert['meta']['underlying_symbol']
    d['vol_oi_ratio'] = alert['meta']['vol_oi_ratio']
    d['volume'] = alert['meta']['volume']
    alerts.append(d)

df = pl.DataFrame(alerts)
# >>> df
# shape: (10, 22)
# df results etc.

# def main():
#     print("Hello from interval-flow-example!")


# if __name__ == "__main__":
#     main()
