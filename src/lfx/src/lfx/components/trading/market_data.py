"""Market data components for real-time price feeds and order books."""

import asyncio
import time
from typing import Any

import httpx
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, IntInput, Output, StrInput
from lfx.schema.data import Data


class PriceFeed(Component):
    """Real-time price feed component for market data."""

    display_name = "Price Feed"
    description = "Get real-time price data from connected exchange"
    icon = "BarChart"
    name = "PriceFeed"

    inputs = [
        DataInput(
            name="exchange_connection",
            display_name="Exchange Connection",
            required=True,
            info="Connection from exchange connector",
        ),
        StrInput(
            name="symbol",
            display_name="Trading Symbol",
            required=True,
            info="Trading pair symbol (e.g., BTCUSDT, ETH-USD)",
        ),
        DropdownInput(
            name="interval",
            display_name="Update Interval",
            options=["1s", "5s", "15s", "1m", "5m", "15m"],
            value="5s",
            info="Price update interval",
        ),
        IntInput(
            name="limit",
            display_name="Historical Candles",
            value=100,
            info="Number of historical candles to fetch",
            advanced=True,
        ),
        BoolInput(
            name="include_orderbook",
            display_name="Include Order Book",
            value=False,
            info="Include order book data",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Price Data",
            name="price_data",
            method="get_price_data",
        ),
    ]

    async def get_price_data(self) -> Data:
        """Fetch real-time price data from exchange."""
        try:
            connection_data = self.exchange_connection.data
            exchange = connection_data.get("exchange")
            base_url = connection_data.get("base_url")

            if exchange == "binance":
                return await self._fetch_binance_price(base_url, connection_data)
            elif exchange == "bybit":
                return await self._fetch_bybit_price(base_url, connection_data)
            elif exchange == "bitmex":
                return await self._fetch_bitmex_price(base_url, connection_data)
            elif exchange == "korea_investment":
                return await self._fetch_korea_investment_price(base_url, connection_data)
            else:
                raise ValueError(f"Unsupported exchange: {exchange}")

        except Exception as e:
            self.log(f"Error fetching price data: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "timestamp": int(time.time() * 1000),
                }
            )

    async def _fetch_binance_price(self, base_url: str, connection_data: dict) -> Data:
        """Fetch price data from Binance."""
        async with httpx.AsyncClient() as client:
            # Get current ticker price
            ticker_url = f"{base_url}/api/v3/ticker/price"
            ticker_response = await client.get(ticker_url, params={"symbol": self.symbol})
            ticker_response.raise_for_status()
            ticker = ticker_response.json()

            # Get 24hr stats
            stats_url = f"{base_url}/api/v3/ticker/24hr"
            stats_response = await client.get(stats_url, params={"symbol": self.symbol})
            stats_response.raise_for_status()
            stats = stats_response.json()

            # Get klines (candlestick data)
            klines_url = f"{base_url}/api/v3/klines"
            klines_params = {
                "symbol": self.symbol,
                "interval": self._convert_interval_to_binance(),
                "limit": self.limit,
            }
            klines_response = await client.get(klines_url, params=klines_params)
            klines_response.raise_for_status()
            klines = klines_response.json()

            # Format klines data
            candles = [
                {
                    "timestamp": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in klines
            ]

            result = {
                "status": "success",
                "exchange": "binance",
                "symbol": self.symbol,
                "current_price": float(ticker["price"]),
                "price_change_24h": float(stats["priceChange"]),
                "price_change_percent_24h": float(stats["priceChangePercent"]),
                "high_24h": float(stats["highPrice"]),
                "low_24h": float(stats["lowPrice"]),
                "volume_24h": float(stats["volume"]),
                "quote_volume_24h": float(stats["quoteVolume"]),
                "candles": candles,
                "timestamp": int(time.time() * 1000),
            }

            # Add order book if requested
            if self.include_orderbook:
                orderbook_url = f"{base_url}/api/v3/depth"
                orderbook_response = await client.get(
                    orderbook_url, params={"symbol": self.symbol, "limit": 20}
                )
                orderbook_response.raise_for_status()
                orderbook = orderbook_response.json()
                result["orderbook"] = {
                    "bids": [[float(b[0]), float(b[1])] for b in orderbook["bids"]],
                    "asks": [[float(a[0]), float(a[1])] for a in orderbook["asks"]],
                }

            self.log(f"Fetched price data for {self.symbol}: ${result['current_price']}")
            return Data(data=result)

    async def _fetch_bybit_price(self, base_url: str, connection_data: dict) -> Data:
        """Fetch price data from Bybit."""
        async with httpx.AsyncClient() as client:
            # Get ticker info
            ticker_url = f"{base_url}/v5/market/tickers"
            params = {"category": connection_data.get("market_type", "linear"), "symbol": self.symbol}
            ticker_response = await client.get(ticker_url, params=params)
            ticker_response.raise_for_status()
            ticker_data = ticker_response.json()

            ticker = ticker_data["result"]["list"][0] if ticker_data["result"]["list"] else {}

            # Get klines
            klines_url = f"{base_url}/v5/market/kline"
            klines_params = {
                "category": connection_data.get("market_type", "linear"),
                "symbol": self.symbol,
                "interval": self._convert_interval_to_bybit(),
                "limit": self.limit,
            }
            klines_response = await client.get(klines_url, params=klines_params)
            klines_response.raise_for_status()
            klines_data = klines_response.json()

            candles = [
                {
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in klines_data["result"]["list"]
            ]

            result = {
                "status": "success",
                "exchange": "bybit",
                "symbol": self.symbol,
                "current_price": float(ticker.get("lastPrice", 0)),
                "price_change_24h": float(ticker.get("price24hPcnt", 0)) * 100,
                "high_24h": float(ticker.get("highPrice24h", 0)),
                "low_24h": float(ticker.get("lowPrice24h", 0)),
                "volume_24h": float(ticker.get("volume24h", 0)),
                "turnover_24h": float(ticker.get("turnover24h", 0)),
                "candles": candles,
                "timestamp": int(time.time() * 1000),
            }

            if self.include_orderbook:
                orderbook_url = f"{base_url}/v5/market/orderbook"
                orderbook_params = {
                    "category": connection_data.get("market_type", "linear"),
                    "symbol": self.symbol,
                    "limit": 20,
                }
                orderbook_response = await client.get(orderbook_url, params=orderbook_params)
                orderbook_response.raise_for_status()
                orderbook_data = orderbook_response.json()
                orderbook = orderbook_data["result"]

                result["orderbook"] = {
                    "bids": [[float(b[0]), float(b[1])] for b in orderbook.get("b", [])],
                    "asks": [[float(a[0]), float(a[1])] for a in orderbook.get("a", [])],
                }

            self.log(f"Fetched price data for {self.symbol}: ${result['current_price']}")
            return Data(data=result)

    async def _fetch_bitmex_price(self, base_url: str, connection_data: dict) -> Data:
        """Fetch price data from BitMEX."""
        async with httpx.AsyncClient() as client:
            # Get instrument data
            instrument_url = f"{base_url}/api/v1/instrument"
            instrument_response = await client.get(instrument_url, params={"symbol": self.symbol})
            instrument_response.raise_for_status()
            instruments = instrument_response.json()
            instrument = instruments[0] if instruments else {}

            # Get trade bucketed data (candles)
            bucketed_url = f"{base_url}/api/v1/trade/bucketed"
            bucketed_params = {
                "binSize": self._convert_interval_to_bitmex(),
                "symbol": self.symbol,
                "count": self.limit,
                "reverse": True,
            }
            bucketed_response = await client.get(bucketed_url, params=bucketed_params)
            bucketed_response.raise_for_status()
            buckets = bucketed_response.json()

            candles = [
                {
                    "timestamp": int(time.mktime(time.strptime(b["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000),
                    "open": float(b["open"]),
                    "high": float(b["high"]),
                    "low": float(b["low"]),
                    "close": float(b["close"]),
                    "volume": float(b["volume"]),
                }
                for b in buckets
            ]

            result = {
                "status": "success",
                "exchange": "bitmex",
                "symbol": self.symbol,
                "current_price": float(instrument.get("lastPrice", 0)),
                "price_change_24h": float(instrument.get("lastChangePcnt", 0)) * 100,
                "high_24h": float(instrument.get("highPrice", 0)),
                "low_24h": float(instrument.get("lowPrice", 0)),
                "volume_24h": float(instrument.get("volume24h", 0)),
                "candles": candles[::-1],  # Reverse to chronological order
                "timestamp": int(time.time() * 1000),
            }

            if self.include_orderbook:
                orderbook_url = f"{base_url}/api/v1/orderBook/L2"
                orderbook_params = {"symbol": self.symbol, "depth": 20}
                orderbook_response = await client.get(orderbook_url, params=orderbook_params)
                orderbook_response.raise_for_status()
                orderbook_data = orderbook_response.json()

                bids = [
                    [float(o["price"]), float(o["size"])]
                    for o in orderbook_data
                    if o["side"] == "Buy"
                ]
                asks = [
                    [float(o["price"]), float(o["size"])]
                    for o in orderbook_data
                    if o["side"] == "Sell"
                ]

                result["orderbook"] = {"bids": bids[:20], "asks": asks[:20]}

            self.log(f"Fetched price data for {self.symbol}: ${result['current_price']}")
            return Data(data=result)

    async def _fetch_korea_investment_price(self, base_url: str, connection_data: dict) -> Data:
        """Fetch price data from Korea Investment & Securities."""
        async with httpx.AsyncClient() as client:
            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {connection_data['access_token']}",
                "appkey": connection_data["app_key"],
                "appsecret": connection_data["app_secret"],
                "tr_id": "FHKST01010100",
            }

            # Get stock price
            price_url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": self.symbol}

            price_response = await client.get(price_url, headers=headers, params=params)
            price_response.raise_for_status()
            price_data = price_response.json()

            output = price_data.get("output", {})

            result = {
                "status": "success",
                "exchange": "korea_investment",
                "symbol": self.symbol,
                "current_price": float(output.get("stck_prpr", 0)),
                "price_change": float(output.get("prdy_vrss", 0)),
                "price_change_percent": float(output.get("prdy_ctrt", 0)),
                "high": float(output.get("stck_hgpr", 0)),
                "low": float(output.get("stck_lwpr", 0)),
                "volume": float(output.get("acml_vol", 0)),
                "timestamp": int(time.time() * 1000),
            }

            self.log(f"Fetched price data for {self.symbol}: ₩{result['current_price']}")
            return Data(data=result)

    def _convert_interval_to_binance(self) -> str:
        """Convert interval to Binance format."""
        mapping = {"1s": "1s", "5s": "1m", "15s": "1m", "1m": "1m", "5m": "5m", "15m": "15m"}
        return mapping.get(self.interval, "1m")

    def _convert_interval_to_bybit(self) -> str:
        """Convert interval to Bybit format."""
        mapping = {"1s": "1", "5s": "1", "15s": "1", "1m": "1", "5m": "5", "15m": "15"}
        return mapping.get(self.interval, "1")

    def _convert_interval_to_bitmex(self) -> str:
        """Convert interval to BitMEX format."""
        mapping = {"1s": "1m", "5s": "1m", "15s": "1m", "1m": "1m", "5m": "5m", "15m": "15m"}
        return mapping.get(self.interval, "1m")

    def build(self):
        return self.get_price_data


class OrderBook(Component):
    """Order book component for detailed market depth analysis."""

    display_name = "Order Book"
    description = "Get detailed order book (market depth) data"
    icon = "List"
    name = "OrderBook"

    inputs = [
        DataInput(
            name="exchange_connection",
            display_name="Exchange Connection",
            required=True,
            info="Connection from exchange connector",
        ),
        StrInput(
            name="symbol",
            display_name="Trading Symbol",
            required=True,
            info="Trading pair symbol",
        ),
        IntInput(
            name="depth",
            display_name="Depth Level",
            value=20,
            info="Number of price levels to fetch",
        ),
    ]

    outputs = [
        Output(
            display_name="Order Book Data",
            name="orderbook_data",
            method="get_orderbook",
        ),
    ]

    async def get_orderbook(self) -> Data:
        """Fetch order book data from exchange."""
        try:
            connection_data = self.exchange_connection.data
            exchange = connection_data.get("exchange")
            base_url = connection_data.get("base_url")

            async with httpx.AsyncClient() as client:
                if exchange == "binance":
                    url = f"{base_url}/api/v3/depth"
                    params = {"symbol": self.symbol, "limit": self.depth}
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    bids = [[float(b[0]), float(b[1])] for b in data["bids"]]
                    asks = [[float(a[0]), float(a[1])] for a in data["asks"]]

                elif exchange == "bybit":
                    url = f"{base_url}/v5/market/orderbook"
                    params = {
                        "category": connection_data.get("market_type", "linear"),
                        "symbol": self.symbol,
                        "limit": self.depth,
                    }
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    orderbook = data["result"]

                    bids = [[float(b[0]), float(b[1])] for b in orderbook.get("b", [])]
                    asks = [[float(a[0]), float(a[1])] for a in orderbook.get("a", [])]

                elif exchange == "bitmex":
                    url = f"{base_url}/api/v1/orderBook/L2"
                    params = {"symbol": self.symbol, "depth": self.depth}
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    bids = [
                        [float(o["price"]), float(o["size"])] for o in data if o["side"] == "Buy"
                    ]
                    asks = [
                        [float(o["price"]), float(o["size"])] for o in data if o["side"] == "Sell"
                    ]

                else:
                    raise ValueError(f"Unsupported exchange: {exchange}")

                # Calculate order book metrics
                bid_volume = sum(b[1] for b in bids)
                ask_volume = sum(a[1] for a in asks)
                spread = asks[0][0] - bids[0][0] if bids and asks else 0
                mid_price = (bids[0][0] + asks[0][0]) / 2 if bids and asks else 0

                result = {
                    "status": "success",
                    "exchange": exchange,
                    "symbol": self.symbol,
                    "bids": bids,
                    "asks": asks,
                    "bid_volume": bid_volume,
                    "ask_volume": ask_volume,
                    "spread": spread,
                    "spread_percent": (spread / mid_price * 100) if mid_price > 0 else 0,
                    "mid_price": mid_price,
                    "imbalance": (bid_volume - ask_volume) / (bid_volume + ask_volume)
                    if (bid_volume + ask_volume) > 0
                    else 0,
                    "timestamp": int(time.time() * 1000),
                }

                self.log(f"Fetched order book for {self.symbol} - Spread: {spread:.2f}")
                return Data(data=result)

        except Exception as e:
            self.log(f"Error fetching order book: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "timestamp": int(time.time() * 1000),
                }
            )

    def build(self):
        return self.get_orderbook
