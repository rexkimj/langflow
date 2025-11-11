"""Trading execution components for order placement and management."""

import hashlib
import hmac
import time
from typing import Any

import httpx
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, FloatInput, IntInput, Output, StrInput
from lfx.schema.data import Data


class OrderExecutor(Component):
    """Execute trading orders on connected exchanges with support for leverage and position management."""

    display_name = "Order Executor"
    description = "Execute buy/sell orders with support for long/short positions and leverage"
    icon = "DollarSign"
    name = "OrderExecutor"

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
            info="Trading pair symbol (e.g., BTCUSDT)",
        ),
        DropdownInput(
            name="side",
            display_name="Order Side",
            options=["buy", "sell"],
            value="buy",
            required=True,
            info="Buy (open long/close short) or Sell (open short/close long)",
        ),
        DropdownInput(
            name="position_side",
            display_name="Position Side",
            options=["long", "short", "both"],
            value="both",
            info="Position side for futures trading",
        ),
        DropdownInput(
            name="order_type",
            display_name="Order Type",
            options=["market", "limit", "stop_loss", "take_profit"],
            value="market",
            required=True,
            info="Type of order to execute",
        ),
        FloatInput(
            name="quantity",
            display_name="Quantity",
            required=True,
            info="Amount to trade",
        ),
        FloatInput(
            name="price",
            display_name="Limit Price",
            value=0.0,
            info="Price for limit orders (0 for market orders)",
        ),
        FloatInput(
            name="stop_price",
            display_name="Stop Price",
            value=0.0,
            info="Trigger price for stop orders",
        ),
        IntInput(
            name="leverage",
            display_name="Leverage",
            value=1,
            info="Leverage multiplier (1-125 depending on exchange)",
        ),
        BoolInput(
            name="reduce_only",
            display_name="Reduce Only",
            value=False,
            info="Only reduce position, don't open new positions",
            advanced=True,
        ),
        BoolInput(
            name="post_only",
            display_name="Post Only",
            value=False,
            info="Ensure order is maker order (limit only)",
            advanced=True,
        ),
        StrInput(
            name="client_order_id",
            display_name="Client Order ID",
            value="",
            info="Custom order ID for tracking",
            advanced=True,
        ),
        BoolInput(
            name="test_mode",
            display_name="Test Mode",
            value=True,
            info="Test order without actual execution",
        ),
    ]

    outputs = [
        Output(
            display_name="Order Result",
            name="order_result",
            method="execute_order",
        ),
    ]

    def _generate_signature(self, secret: str, message: str) -> str:
        """Generate HMAC signature for API authentication."""
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    async def execute_order(self) -> Data:
        """Execute trading order on the connected exchange."""
        try:
            connection_data = self.exchange_connection.data
            exchange = connection_data.get("exchange")

            if exchange == "binance":
                return await self._execute_binance_order(connection_data)
            elif exchange == "bybit":
                return await self._execute_bybit_order(connection_data)
            elif exchange == "bitmex":
                return await self._execute_bitmex_order(connection_data)
            elif exchange == "korea_investment":
                return await self._execute_korea_investment_order(connection_data)
            else:
                raise ValueError(f"Unsupported exchange: {exchange}")

        except Exception as e:
            self.log(f"Order execution error: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "timestamp": int(time.time() * 1000),
                }
            )

    async def _execute_binance_order(self, connection_data: dict) -> Data:
        """Execute order on Binance."""
        base_url = connection_data.get("base_url")
        api_key = connection_data.get("api_key")
        api_secret = connection_data.get("api_secret")
        market_type = connection_data.get("market_type")

        async with httpx.AsyncClient() as client:
            # Set leverage for futures
            if market_type == "futures" and self.leverage > 1:
                leverage_url = f"{base_url}/fapi/v1/leverage"
                timestamp = int(time.time() * 1000)
                leverage_params = f"symbol={self.symbol}&leverage={self.leverage}&timestamp={timestamp}"
                signature = self._generate_signature(api_secret, leverage_params)

                headers = {"X-MBX-APIKEY": api_key}
                await client.post(
                    f"{leverage_url}?{leverage_params}&signature={signature}",
                    headers=headers,
                )
                self.log(f"Set leverage to {self.leverage}x")

            # Prepare order parameters
            timestamp = int(time.time() * 1000)
            order_params = {
                "symbol": self.symbol,
                "side": self.side.upper(),
                "type": self._convert_order_type_binance(),
                "timestamp": timestamp,
            }

            # Add quantity
            if market_type == "futures":
                order_params["quantity"] = self.quantity
                if self.position_side != "both":
                    order_params["positionSide"] = self.position_side.upper()
            else:
                order_params["quantity"] = self.quantity

            # Add price for limit orders
            if self.order_type == "limit":
                order_params["price"] = self.price
                order_params["timeInForce"] = "GTC"
                if self.post_only:
                    order_params["timeInForce"] = "GTX"

            # Add stop price for stop orders
            if self.order_type in ["stop_loss", "take_profit"]:
                order_params["stopPrice"] = self.stop_price

            if self.reduce_only:
                order_params["reduceOnly"] = "true"

            if self.client_order_id:
                order_params["newClientOrderId"] = self.client_order_id

            # Generate signature
            query_string = "&".join([f"{k}={v}" for k, v in sorted(order_params.items())])
            signature = self._generate_signature(api_secret, query_string)

            # Choose endpoint
            if self.test_mode:
                endpoint = "/api/v3/order/test" if market_type == "spot" else "/fapi/v1/order/test"
            else:
                endpoint = "/api/v3/order" if market_type == "spot" else "/fapi/v1/order"

            url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
            headers = {"X-MBX-APIKEY": api_key}

            response = await client.post(url, headers=headers)
            response.raise_for_status()

            result = response.json() if not self.test_mode else {"status": "TEST_SUCCESS"}

            self.log(
                f"Order executed: {self.side.upper()} {self.quantity} {self.symbol} @ {self.price or 'MARKET'}"
            )

            return Data(
                data={
                    "status": "success",
                    "exchange": "binance",
                    "order_id": result.get("orderId", "test"),
                    "symbol": self.symbol,
                    "side": self.side,
                    "position_side": self.position_side,
                    "order_type": self.order_type,
                    "quantity": self.quantity,
                    "price": self.price,
                    "leverage": self.leverage,
                    "test_mode": self.test_mode,
                    "order_details": result,
                    "timestamp": int(time.time() * 1000),
                }
            )

    async def _execute_bybit_order(self, connection_data: dict) -> Data:
        """Execute order on Bybit."""
        base_url = connection_data.get("base_url")
        api_key = connection_data.get("api_key")
        api_secret = connection_data.get("api_secret")
        market_type = connection_data.get("market_type")

        async with httpx.AsyncClient() as client:
            # Set leverage
            if self.leverage > 1:
                timestamp = str(int(time.time() * 1000))
                recv_window = "5000"

                leverage_body = {
                    "category": market_type,
                    "symbol": self.symbol,
                    "buyLeverage": str(self.leverage),
                    "sellLeverage": str(self.leverage),
                }

                leverage_str = "&".join([f"{k}={v}" for k, v in leverage_body.items()])
                param_str = f"{timestamp}{api_key}{recv_window}{leverage_str}"
                signature = self._generate_signature(api_secret, param_str)

                headers = {
                    "X-BAPI-API-KEY": api_key,
                    "X-BAPI-TIMESTAMP": timestamp,
                    "X-BAPI-SIGN": signature,
                    "X-BAPI-RECV-WINDOW": recv_window,
                }

                leverage_url = f"{base_url}/v5/position/set-leverage"
                await client.post(leverage_url, headers=headers, json=leverage_body)
                self.log(f"Set leverage to {self.leverage}x")

            # Prepare order
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"

            order_body = {
                "category": market_type,
                "symbol": self.symbol,
                "side": self.side.capitalize(),
                "orderType": self._convert_order_type_bybit(),
                "qty": str(self.quantity),
            }

            if self.order_type == "limit":
                order_body["price"] = str(self.price)
                if self.post_only:
                    order_body["timeInForce"] = "PostOnly"

            if self.order_type in ["stop_loss", "take_profit"]:
                order_body["triggerPrice"] = str(self.stop_price)

            if self.reduce_only:
                order_body["reduceOnly"] = True

            if self.position_side != "both":
                order_body["positionIdx"] = 1 if self.position_side == "long" else 2

            if self.client_order_id:
                order_body["orderLinkId"] = self.client_order_id

            # Generate signature
            order_str = "&".join([f"{k}={v}" for k, v in sorted(order_body.items())])
            param_str = f"{timestamp}{api_key}{recv_window}{order_str}"
            signature = self._generate_signature(api_secret, param_str)

            headers = {
                "X-BAPI-API-KEY": api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": signature,
                "X-BAPI-RECV-WINDOW": recv_window,
            }

            # Execute order
            endpoint = "/v5/order/create"
            url = f"{base_url}{endpoint}"

            if self.test_mode:
                self.log("TEST MODE: Order would be placed with following parameters:")
                self.log(str(order_body))
                result = {"status": "TEST_SUCCESS", "orderLinkId": "test"}
            else:
                response = await client.post(url, headers=headers, json=order_body)
                response.raise_for_status()
                result = response.json()["result"]

            self.log(
                f"Order executed: {self.side.upper()} {self.quantity} {self.symbol} @ {self.price or 'MARKET'}"
            )

            return Data(
                data={
                    "status": "success",
                    "exchange": "bybit",
                    "order_id": result.get("orderId", "test"),
                    "symbol": self.symbol,
                    "side": self.side,
                    "position_side": self.position_side,
                    "order_type": self.order_type,
                    "quantity": self.quantity,
                    "price": self.price,
                    "leverage": self.leverage,
                    "test_mode": self.test_mode,
                    "order_details": result,
                    "timestamp": int(time.time() * 1000),
                }
            )

    async def _execute_bitmex_order(self, connection_data: dict) -> Data:
        """Execute order on BitMEX."""
        base_url = connection_data.get("base_url")
        api_key = connection_data.get("api_key")
        api_secret = connection_data.get("api_secret")

        async with httpx.AsyncClient() as client:
            # Prepare order
            verb = "POST"
            path = "/api/v1/order"
            expires = int(time.time()) + 60

            order_data = {
                "symbol": self.symbol,
                "side": self.side.capitalize(),
                "orderQty": self.quantity if self.side == "buy" else -self.quantity,
                "ordType": self._convert_order_type_bitmex(),
            }

            if self.order_type == "limit":
                order_data["price"] = self.price

            if self.order_type in ["stop_loss", "take_profit"]:
                order_data["stopPx"] = self.stop_price

            if self.reduce_only:
                order_data["execInst"] = "ReduceOnly"

            if self.client_order_id:
                order_data["clOrdID"] = self.client_order_id

            # Generate signature
            import json

            body = json.dumps(order_data)
            message = f"{verb}{path}{expires}{body}"
            signature = hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()

            headers = {
                "api-expires": str(expires),
                "api-key": api_key,
                "api-signature": signature,
                "Content-Type": "application/json",
            }

            url = f"{base_url}{path}"

            if self.test_mode:
                self.log("TEST MODE: Order would be placed with following parameters:")
                self.log(str(order_data))
                result = {"status": "TEST_SUCCESS", "orderID": "test"}
            else:
                response = await client.post(url, headers=headers, json=order_data)
                response.raise_for_status()
                result = response.json()

            self.log(
                f"Order executed: {self.side.upper()} {self.quantity} {self.symbol} @ {self.price or 'MARKET'}"
            )

            return Data(
                data={
                    "status": "success",
                    "exchange": "bitmex",
                    "order_id": result.get("orderID", "test"),
                    "symbol": self.symbol,
                    "side": self.side,
                    "order_type": self.order_type,
                    "quantity": self.quantity,
                    "price": self.price,
                    "test_mode": self.test_mode,
                    "order_details": result,
                    "timestamp": int(time.time() * 1000),
                }
            )

    async def _execute_korea_investment_order(self, connection_data: dict) -> Data:
        """Execute order on Korea Investment & Securities."""
        base_url = connection_data.get("base_url")
        access_token = connection_data.get("access_token")
        app_key = connection_data.get("app_key")
        app_secret = connection_data.get("app_secret")
        account_number = connection_data.get("account_number")
        environment = connection_data.get("environment")

        async with httpx.AsyncClient() as client:
            # Determine transaction ID based on order type and side
            if self.side == "buy":
                tr_id = "VTTC0802U" if environment == "virtual" else "TTTC0802U"
            else:
                tr_id = "VTTC0801U" if environment == "virtual" else "TTTC0801U"

            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {access_token}",
                "appkey": app_key,
                "appsecret": app_secret,
                "tr_id": tr_id,
            }

            # Prepare order data
            order_data = {
                "CANO": account_number.split("-")[0],
                "ACNT_PRDT_CD": account_number.split("-")[1],
                "PDNO": self.symbol,
                "ORD_DVSN": "01" if self.order_type == "market" else "00",  # 01: market, 00: limit
                "ORD_QTY": str(int(self.quantity)),
                "ORD_UNPR": str(int(self.price)) if self.order_type == "limit" else "0",
            }

            url = f"{base_url}/uapi/domestic-stock/v1/trading/order-cash"

            if self.test_mode:
                self.log("TEST MODE: Order would be placed with following parameters:")
                self.log(str(order_data))
                result = {"status": "TEST_SUCCESS", "output": {"KRX_FWDG_ORD_ORGNO": "test"}}
            else:
                response = await client.post(url, headers=headers, json=order_data)
                response.raise_for_status()
                result = response.json()

            self.log(
                f"Order executed: {self.side.upper()} {self.quantity} {self.symbol} @ {self.price or 'MARKET'}"
            )

            return Data(
                data={
                    "status": "success",
                    "exchange": "korea_investment",
                    "order_id": result.get("output", {}).get("KRX_FWDG_ORD_ORGNO", "test"),
                    "symbol": self.symbol,
                    "side": self.side,
                    "order_type": self.order_type,
                    "quantity": self.quantity,
                    "price": self.price,
                    "test_mode": self.test_mode,
                    "order_details": result,
                    "timestamp": int(time.time() * 1000),
                }
            )

    def _convert_order_type_binance(self) -> str:
        """Convert order type to Binance format."""
        mapping = {
            "market": "MARKET",
            "limit": "LIMIT",
            "stop_loss": "STOP_LOSS",
            "take_profit": "TAKE_PROFIT",
        }
        return mapping.get(self.order_type, "MARKET")

    def _convert_order_type_bybit(self) -> str:
        """Convert order type to Bybit format."""
        mapping = {
            "market": "Market",
            "limit": "Limit",
            "stop_loss": "Market",
            "take_profit": "Market",
        }
        return mapping.get(self.order_type, "Market")

    def _convert_order_type_bitmex(self) -> str:
        """Convert order type to BitMEX format."""
        mapping = {
            "market": "Market",
            "limit": "Limit",
            "stop_loss": "Stop",
            "take_profit": "MarketIfTouched",
        }
        return mapping.get(self.order_type, "Market")

    def build(self):
        return self.execute_order
