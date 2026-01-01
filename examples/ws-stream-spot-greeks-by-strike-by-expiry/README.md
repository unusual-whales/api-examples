# Stream Spot Greeks by Strike and by Expiry to a DuckDB Database
This python script demonstrates Spot Greeks by Strike and by Expiry-specific websocket functionality:
- Connect to the websocket then join a few channels (you can adjust this to your liking) following the `gex_strike_expiry:{ticker}` pattern:
  - `gex_strike_expiry:SPY`
  - `gex_strike_expiry:NFLX`
  - `gex_strike_expiry:TSLA`
  - `gex_strike_expiry:GOOGL`
- Use a buffer to temporarily store data before writing to DuckDB (every 500 records or every 10 seconds, whichever comes first)
- Automatic reconnect (tries 5 times before it quits)

## Notes
- The "spot_greeks_by_strike_by_expiry.duckdb" database is not included in this demo repo as it is too large, **for reference running this script for 25 minutes on these 4 tickers yields 295219 records and a 199 MB database**
- `setup_logging()`: creates and configures the `logger`
- `async setup_database()`: creates the DuckDB database and table "spot_greeks_by_strike_by_expiry"
- `validate_payload()`: validates the websocket message payload
- `parse_payload()`: parses the websocket message payload into a dictionary
- `flush_buffer_to_db`: write parsed data from the buffer into the DuckDB database
- `async stream_websocket_to_buffer()`: join channels, received messages, and store parsed data in buffer
- `async connect_and_stream()`: connect to websocket and handle reconnection logic
- `signal_handler()`: allow for "graceful" `Ctrl+C` shutdown of program
- `async main()`: the main loop

## Run the script
From the directory containing `ws_stream_spot_greeks_by_strike_by_expiry.py` and `requirements.txt` on a Ubuntu instance running on Windows WSL2:

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

4. Launch the script
```
$ python ws_stream_spot_greeks_by_strike_by_expiry.py
```

5. Exit the script with `Ctrl+C`

## Quick Database Exploration
The DuckDB database is created in the same directory as the script for easy review.

1. If not already installed, install `duckdb` ([https://duckdb.org/](https://duckdb.org/))
```
$ curl https://install.duckdb.org | sh
```

2. Connect to the database
```
$ duckdb spot_greeks_by_strike_by_expiry.duckdb
```

3. Now that you are in the DuckDB CLI tool, turn on headers then generate a markdown summary of the data set for easy reference (note that the DuckDB CLI tool turns your prompt into a `D` character):
```
D .headers on
D .mode markdown
D .once 'summary.md'
D SUMMARIZE spot_greeks_by_strike_by_expiry;
```

4. You can now review the `summary.md` file, which includes valuable information like column data type, min, max, etc.

|    column_name     | column_type |                 min                  |                 max                 | approx_unique |            avg             |        std         |            q25             |            q50             |            q75             | count  | null_percentage |
|--------------------|-------------|--------------------------------------|-------------------------------------|--------------:|----------------------------|--------------------|----------------------------|----------------------------|----------------------------|-------:|----------------:|
| ticker             | VARCHAR     | GOOGL                                | TSLA                                | 4             | NULL                       | NULL               | NULL                       | NULL                       | NULL                       | 295219 | 0.00            |
| expiry             | DATE        | 2025-12-31                           | 2028-06-16                          | 42            | 2026-08-27 09:40:38.147951 | NULL               | 2026-01-26                 | 2026-05-15                 | 2027-01-13                 | 295219 | 0.00            |
| strike_price       | DOUBLE      | 0.5                                  | 1360.0                              | 796           | 427.88312913464245         | 275.87947930348673 | 169.82156599842605         | 423.0126871097166          | 657.6542238341306          | 295219 | 0.00            |
| strike_price_cents | INTEGER     | 50                                   | 136000                              | 812           | 42788.312913464244         | 27587.947930348622 | 16982                      | 42303                      | 65767                      | 295219 | 0.00            |
| timestamp_ms       | BIGINT      | 1767194698000                        | 1767196212000                       | 148           | 1767195449786.2544         | 433460.78428421356 | 1767195075655              | 1767195445867              | 1767195822094              | 295219 | 0.00            |
| timestamp_dt       | TIMESTAMP   | 2025-12-31 09:24:58                  | 2025-12-31 09:50:12                 | 126           | 2025-12-31 09:37:29.786254 | NULL               | 2025-12-31 09:31:15.654926 | 2025-12-31 09:37:25.866964 | 2025-12-31 09:43:42.093833 | 295219 | 0.00            |
| date               | DATE        | 2025-12-31                           | 2025-12-31                          | 1             | 2025-12-31 00:00:00        | NULL               | 2025-12-31                 | 2025-12-31                 | 2025-12-31                 | 295219 | 0.00            |
| time               | TIME        | 15:24:58                             | 15:50:12                            | 132           | 15:37:29.786254            | NULL               | 15:31:15.654926            | 15:37:25.866964            | 15:43:42.093832            | 295219 | 0.00            |
| underlying_price   | DOUBLE      | 93.4159                              | 685.62                              | 174           | 440.13120933539903         | 228.0256655940454  | 313.54662905029824         | 454.5810447943895          | 685.1095590418886          | 295219 | 0.00            |
| call_delta_oi      | DOUBLE      | 0.0                                  | 0.0                                 | 1             | 0.0                        | 0.0                | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_delta_oi       | DOUBLE      | 0.0                                  | 0.0                                 | 1             | 0.0                        | 0.0                | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_gamma_oi      | DOUBLE      | 0.0                                  | 1594300646.75664                    | 325985        | 3345357.316140159          | 37549593.43836072  | 608.1840473230144          | 16174.285559387436         | 213496.7571586976          | 295219 | 0.00            |
| put_gamma_oi       | DOUBLE      | -2365417329.197996                   | 0.0                                 | 191375        | -3722144.1287039015        | 45450419.15446872  | -165208.1082590586         | -7130.048271568935         | 0.0                        | 295219 | 0.00            |
| call_charm_oi      | DOUBLE      | -467978234060.215                    | 42166031896.19006                   | 236069        | -207973793.75276315        | 5939405085.0394945 | -2116364.115909089         | -89791.50822493681         | -1.921487128379034         | 295219 | 0.00            |
| put_charm_oi       | DOUBLE      | -211519897305.8648                   | 26757058992.68951                   | 199290        | -161796688.07519424        | 3743914702.480285  | 0.0                        | 7869.324360237493          | 443143.70361037645         | 295219 | 0.00            |
| call_vanna_oi      | DOUBLE      | -29445914.90182759                   | 74888523.3011572                    | 273002        | 137051.47048132683         | 1843227.3381446826 | -470.973799562022          | 335.1612144363771          | 22220.308817692592         | 295219 | 0.00            |
| put_vanna_oi       | DOUBLE      | -11486564.85714325                   | 65961320.5521606                    | 279971        | 321982.2547114152          | 2307693.692005146  | -3.3549473120607076        | 2.908001183827112e-05      | 22172.5608690249           | 295219 | 0.00            |
| call_delta_vol     | DOUBLE      | 0.0                                  | 0.0                                 | 1             | 0.0                        | 0.0                | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_delta_vol      | DOUBLE      | 0.0                                  | 0.0                                 | 1             | 0.0                        | 0.0                | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_gamma_vol     | DOUBLE      | 0.0                                  | 12573426874.88632                   | 73180         | 6786582.768199699          | 211279489.58435556 | 0.0                        | 0.0                        | 267.1883403081548          | 295219 | 0.00            |
| put_gamma_vol      | DOUBLE      | -14421767625.27642                   | 0.0                                 | 119559        | -7840136.435769927         | 240559993.16111007 | -32.037832409537906        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_charm_vol     | DOUBLE      | -347653517776.5828                   | 10339829711.89835                   | 89264         | -203089044.74234653        | 6184869756.879654  | -474.491481568274          | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_charm_vol      | DOUBLE      | -99521154970.0538                    | 188241637993.863                    | 77726         | -4580964.4807453025        | 3040917086.920335  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_vanna_vol     | DOUBLE      | -7340240.05648933                    | 83592198.9046542                    | 120843        | 56651.584657547246         | 1459720.1874066037 | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_vanna_vol      | DOUBLE      | -36255420.51973382                   | 29999246.26360568                   | 102229        | 29431.61624243812          | 824876.3570004054  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_gamma_ask_vol | DOUBLE      | -5568158538.969                      | 0.0                                 | 82887         | -2995570.766641341         | 93908009.37199348  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_gamma_bid_vol | DOUBLE      | 0.0                                  | 6762937214.36473                    | 56635         | 3548265.621228936          | 112282019.0625348  | 0.0                        | 0.0                        | 3.3338566167660076e-06     | 295219 | 0.00            |
| put_gamma_ask_vol  | DOUBLE      | -6941184064.68148                    | 0.0                                 | 61625         | -3772842.538944183         | 115240642.78345297 | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_gamma_bid_vol  | DOUBLE      | 0.0                                  | 7262029492.99698                    | 58184         | 3798397.236358318          | 120033688.00464319 | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_charm_ask_vol | DOUBLE      | -4194179100.241977                   | 148064041275.8164                   | 54194         | 88411112.56885828          | 2711410703.307197  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_charm_bid_vol | DOUBLE      | -196752346387.4318                   | 6890413693.62003                    | 59640         | -112130126.88385387        | 3438586982.118314  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_charm_ask_vol  | DOUBLE      | -50290445919.6473                    | 90136930402.9396                    | 56778         | -4182498.477715022         | 1468469742.3142385 | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_charm_bid_vol  | DOUBLE      | -92454807005.5473                    | 48608950060.2091                    | 78746         | 3106039.578445813          | 1472799283.2689738 | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_vanna_ask_vol | DOUBLE      | -35681031.13437481                   | 3088292.657059363                   | 64096         | -24074.13855842115         | 636402.4060673853  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| call_vanna_bid_vol | DOUBLE      | -3598495.839568985                   | 47224688.5037768                    | 69810         | 31942.973901693185         | 827191.8092420193  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_vanna_ask_vol  | DOUBLE      | -17360411.60151345                   | 15230999.90076428                   | 47681         | 15207.941767400283         | 418435.8487773353  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| put_vanna_bid_vol  | DOUBLE      | -14621154.17465628                   | 17806835.63307196                   | 69854         | -12997.709924566912        | 391030.0223632001  | 0.0                        | 0.0                        | 0.0                        | 295219 | 0.00            |
| option_key         | VARCHAR     | GOOGL|2026-01-02|10000|1767194710000 | TSLA|2028-06-16|99000|1767196152000 | 269148        | NULL                       | NULL               | NULL                       | NULL                       | NULL                       | 295219 | 0.00            |
| inserted_at        | TIMESTAMP   | 2025-12-31 09:24:57.01827            | 2025-12-31 09:50:11.497353          | 706           | 2025-12-31 09:37:30.916219 | NULL               | 2025-12-31 09:31:13.513686 | 2025-12-31 09:37:25.977003 | 2025-12-31 09:43:45.01479  | 295219 | 0.00            |

5. Let's do something not possible on the Unusual Whales web platform: calculate the OI-based gamma exposure using a combined subset of expiries. (You can execute a multi-line query in the DuckDB CLI tool by simply hitting enter and building the query until you end it with the semincolon `;` character.)
```
D SELECT
    strike_price,
    SUM(call_gamma_oi) AS subset_call_gamma_oi,
    SUM(put_gamma_oi) AS subset_put_gamma_oi,
    SUM(call_gamma_oi) + SUM(put_gamma_oi) AS subset_net_gamma_oi
  FROM spot_greeks_by_strike_by_expiry
  WHERE
    ticker = 'NFLX'
    AND strike_price BETWEEN 90 AND 100
    AND expiry IN ('2026-01-02', '2026-01-09', '2026-01-16')
  GROUP BY strike_price
  ORDER BY strike_price DESC;
```

which gives you this result:
```
 ──────────────┬──────────────────────┬─────────────────────┬─────────────────────┐
│ strike_price │ subset_call_gamma_oi │ subset_put_gamma_oi │ subset_net_gamma_oi │
│    double    │        double        │       double        │       double        │
├──────────────┼──────────────────────┼─────────────────────┼─────────────────────┤
│        100.0 │    753393568.1834271 │ -340653878.53131306 │  412739689.65211403 │
│         99.5 │   19268068.186631702 │  -16516919.24491694 │   2751148.941714762 │
│         99.0 │   104030534.14679566 │  -91678377.35301389 │  12352156.793781772 │
│         98.5 │   21218345.647722002 │  -36306481.85478935 │ -15088136.207067344 │
│         98.0 │   237932989.14382252 │ -124103404.05619262 │   113829585.0876299 │
│         97.5 │    48170065.89897284 │  -62895198.57094134 │ -14725132.671968497 │
│         97.0 │   235711224.46366745 │  -83844471.06545734 │   151866753.3982101 │
│         96.5 │    91545048.29343313 │  -44750565.44145513 │     46794482.851978 │
│         96.0 │    289017505.6684144 │ -178792404.58537692 │   110225101.0830375 │
│         95.5 │    172790522.2467746 │  -71022526.52971222 │   101767995.7170624 │
│         95.0 │   1669405008.9913805 │  -740782895.8743676 │   928622113.1170129 │
│         94.5 │    217180449.4261429 │  -269014315.6469307 │  -51833866.22078779 │
│         94.0 │    676111851.3713803 │  -465140020.8464424 │  210971830.52493793 │
│         93.5 │    332183275.0421978 │ -295910939.77028143 │   36272335.27191639 │
│         93.0 │   365597750.54323435 │  -593433262.0049942 │  -227835511.4617598 │
│         92.5 │     76316004.3604843 │ -201650122.10249916 │ -125334117.74201486 │
│         92.0 │    134439063.7989933 │  -380058647.1062367 │  -245619583.3072434 │
│         91.5 │   13464356.790212762 │  -79884049.65992364 │  -66419692.86971088 │
│         91.0 │   32802111.344166793 │ -137657363.67767015 │ -104855252.33350337 │
│         90.5 │   2527922.6771054836 │ -16435187.779206343 │  -13907265.10210086 │
│         90.0 │   124437720.05768451 │  -652556652.6751091 │  -528118932.6174246 │
├──────────────┴──────────────────────┴─────────────────────┴─────────────────────┤
│ 21 rows                                                               4 columns │
└─────────────────────────────────────────────────────────────────────────────────┘
```
