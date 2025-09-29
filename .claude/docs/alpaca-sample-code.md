## Paper Trading Auth
Alpaca’s paper trading service uses a different domain and different credentials from the live API. You’ll need to connect to the right domain so that you don’t run your paper trading algo on your live account.

To use the paper trading api, set APCA-API-KEY-ID and APCA-API-SECRET-KEY to your paper credentials, and set the domain to https://paper-api.alpaca.markets.

After you have tested your algo in the paper environment and are ready to start running your algo in the live environment, you can switch the domain to the live domain, and the credentials to your live credentials. Your algo will then start trading with real money.

## Orders

### Place new orders
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

trading_client = TradingClient('api-key', 'secret-key', paper=True)

### preparing market order
market_order_data = MarketOrderRequest(
                    symbol="SPY",
                    qty=0.023,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                    )

### Market order
market_order = trading_client.submit_order(
                order_data=market_order_data
               )

### Sample code for POST for creating new order

import requests

url = "https://paper-api.alpaca.markets/v2/orders"

payload = {
    "type": "market",
    "time_in_force": "day",
    "notional": "1000",
    "symbol": "AAPL",
    "client_order_id": "congress",
    "side": "buy"
}
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "APCA-API-KEY-ID": "PK57TZ9AYRTU7JZCM9MO",
    "APCA-API-SECRET-KEY": "FRhMgaJ2bArZ3CNkAF6M1xxAeQryFMXczUxF4WLh"
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)

### Sample response for POST for creating new order
{
  "id": "b1f781ba-e4b1-44ae-a129-c41239e50afd",
  "client_order_id": "congress",
  "created_at": "2025-09-22T03:58:04.935042273Z",
  "updated_at": "2025-09-22T03:58:04.937296713Z",
  "submitted_at": "2025-09-22T03:58:04.935042273Z",
  "filled_at": null,
  "expired_at": null,
  "canceled_at": null,
  "failed_at": null,
  "replaced_at": null,
  "replaced_by": null,
  "replaces": null,
  "asset_id": "b0b6dd9d-8b9b-48a9-ba46-b9d54906e415",
  "symbol": "AAPL",
  "asset_class": "us_equity",
  "notional": "1000",
  "qty": null,
  "filled_qty": "0",
  "filled_avg_price": null,
  "order_class": "",
  "order_type": "market",
  "type": "market",
  "side": "buy",
  "position_intent": "buy_to_open",
  "time_in_force": "day",
  "limit_price": null,
  "stop_price": null,
  "status": "accepted",
  "extended_hours": false,
  "legs": null,
  "trail_percent": null,
  "trail_price": null,
  "hwm": null,
  "subtag": null,
  "source": null,
  "expires_at": "2025-09-22T20:00:00Z"
}

### preparing limit order
limit_order_data = LimitOrderRequest(
                    symbol="BTC/USD",
                    limit_price=17000,
                    notional=4000,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.FOK
                   )

### Limit order
limit_order = trading_client.submit_order(
                order_data=limit_order_data
              )


## Submit shorts
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

## Using Client Order IDs

client_order_id can be used to organize and track specific orders in your client program. Unique client_order_ids for different strategies is a good way of running parallel algos across the same account.

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

trading_client = TradingClient('api-key', 'secret-key', paper=True)

# preparing orders
market_order_data = MarketOrderRequest(
                    symbol="SPY",
                    qty=0.023,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    client_order_id='my_first_order',
                    )

# Market order
market_order = trading_client.submit_order(
                order_data=market_order_data
               )

# Get our order using its Client Order ID.
my_order = trading_client.get_order_by_client_id('my_first_order')
print('Got order #{}'.format(my_order.id))

## Positions
You can view the positions in your portfolio by making a GET request to the /v2/positions endpoint. If you specify a symbol, you’ll see only your position for the associated stock.

### Get Request for Positions
import requests

url = "https://paper-api.alpaca.markets/v2/positions"

headers = {
    "accept": "application/json",
    "APCA-API-KEY-ID": "PK57TZ9AYRTU7JZCM9MO",
    "APCA-API-SECRET-KEY": "FRhMgaJ2bArZ3CNkAF6M1xxAeQryFMXczUxF4WLh"
}

response = requests.get(url, headers=headers)

print(response.text)

### Example Response for Get Request for Positions

[
  {
    "asset_id": "cf80d13f-470c-4947-8593-c5e098aeba4e",
    "symbol": "CRM",
    "exchange": "NYSE",
    "asset_class": "us_equity",
    "asset_marginable": true,
    "qty": "4.180203894",
    "avg_entry_price": "239.220389",
    "side": "long",
    "market_value": "1032.88658",
    "cost_basis": "999.99",
    "unrealized_pl": "32.89658",
    "unrealized_plpc": "0.0328969089690897",
    "unrealized_intraday_pl": "0",
    "unrealized_intraday_plpc": "0",
    "current_price": "247.09",
    "lastday_price": "247.09",
    "change_today": "0",
    "qty_available": "4.180203894"
  },
  {
    "asset_id": "42f6d400-741b-4a18-ae61-73faae71e2cb",
    "symbol": "DHR",
    "exchange": "NYSE",
    "asset_class": "us_equity",
    "asset_marginable": true,
    "qty": "2.92227647",
    "avg_entry_price": "203.156",
    "side": "long",
    "market_value": "564.846819",
    "cost_basis": "593.677999",
    "unrealized_pl": "-28.83118",
    "unrealized_plpc": "-0.0485636659073836",
    "unrealized_intraday_pl": "0",
    "unrealized_intraday_plpc": "0",
    "current_price": "193.29",
    "lastday_price": "193.29",
    "change_today": "0",
    "qty_available": "2.92227647"
  }

The current price reflected will be based on the following:

4:00 am ET - 9:30 am ET - Last trade based on the premarket
9:30 am ET - 4pm ET - Last trade
4:00 pm ET - 10:00 pm ET - Last trade based on after-hours trading
10 pm ET - 4:00 am ET next trading day - Official closing price from the primary exchange at 4 pm ET.

# Retrive market clock
