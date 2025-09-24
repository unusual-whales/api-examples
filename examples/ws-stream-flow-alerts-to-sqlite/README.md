# Stream Flow Alerts to a SQLite Database
This python script demonstrates Flow Alert-specific websocket functionality:
- Connect to the websocket and join the `flow-alerts` channel
- Use a buffer to temporarily store Flow Alert data before writing to the SQLite database (every 1 second)
- Automatic reconnect (tries 5 times before it quits)

### Quick Database Exploration
From your terminal, connect to the database:
```
sqlite3 flow_alerts.db
```

Now that you are in the SQLite terminal, turn on headers and column mode for pretty printing:
```
sqlite> .headers on
sqlite> .mode column
```

This is a small sample database created from approximately 2 minutes of Flow Alert streaming:
```
sqlite> SELECT COUNT(*) FROM flow_alerts;
56
```

Explore the data:
```
sqlite> SELECT executed_at,ticker,option_chain,ask_vol,total_ask_side_prem,price FROM flow_alerts WHERE rule_name = 'RepeatedHits';
executed_at    ticker  option_chain         ask_vol  total_ask_side_prem  price
-------------  ------  -------------------  -------  -------------------  -----
1758212429295  CRCL    CRCL250919P00132000  563      48396.0              1.48 
1758212430668  ASTS    ASTS251219C00055000  5        0.0                  3.4  
1758212434794  ELF     ELF251003C00150000   78       24225.0              4.25 
1758212434793  ELF     ELF250926C00146000   59       21930.0              4.3  
1758212434793  ELF     ELF251003C00149000   40       17670.0              4.65 
1758212436863  MU      MU251017C00240000    35       805.0                1.14 
1758212437532  ETHA    ETHA250919C00033000  798      34200.0              2.0  
1758212437656  ETHA    ETHA250919C00033000  872      14800.0              2.0  
1758212440144  CCJ     CCJ251017C00085000   322      0.0                  3.45 
1758212445090  CCJ     CCJ251017C00085000   338      5520.0               3.45 
1758212448061  MP      MP250919C00065000    270      34200.0              6.0  
1758212454154  HIMS    HIMS251017P00030000  2878     19824.0              0.12
... more results
```


### Notes
- `setup_logging()`: creates and configures the `logger`
- `async create_database_table()`: creates the SQLite table "flow_alerts"
- `async flush_buffers_to_db`: write messages from the buffer to the SQLite database
- `async connect_websocket()`: the key function that interacts with the Unusual Whales websocket, if you are starting from this demo script then the adjustments you will make are almost certainly going to be in this function
- `async main()`: the main loop
