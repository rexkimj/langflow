"""Portfolio management components for tracking positions and account balances."""

import hashlib
import hmac
import time
from typing import Any

import httpx
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, FloatInput, IntInput, Output, StrInput
from lfx.schema.data import Data


class PortfolioManager(Component):
    """Manage and track portfolio positions, balances, and performance metrics."""

    display_name = "Portfolio Manager"
    description = "Track portfolio positions, balances, and calculate performance metrics"
    icon = "Briefcase"
    name = "PortfolioManager"

    inputs = [
        DataInput(
            name="exchange_connection",
            display_name="Exchange Connection",
            required=True,
            info="Connection from exchange connector",
        ),
        BoolInput(
            name="include_open_orders",
            display_name="Include Open Orders",
            value=True,
            info="Include open orders in portfolio data",
        ),
        BoolInput(
            name="include_positions",
            display_name="Include Positions",
            value=True,
            info="Include open positions (for futures)",
        ),
        BoolInput(
            name="calculate_pnl",
            display_name="Calculate PnL",
            value=True,
            info="Calculate profit and loss",
        ),
        StrInput(
            name="quote_currency",
            display_name="Quote Currency",
            value="USDT",
            info="Quote currency for portfolio valuation (USDT, USD, KRW)",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Portfolio Data",
            name="portfolio_data",
            method="get_portfolio",
        ),
    ]

    def _generate_signature(self, secret: str, message: str) -> str:
        """Generate HMAC signature for API authentication."""
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    async def get_portfolio(self) -> Data:
        """Fetch and analyze portfolio data."""
        try:
            connection_data = self.exchange_connection.data
            exchange = connection_data.get("exchange")

            if exchange == "binance":
                return await self._get_binance_portfolio(connection_data)
            elif exchange == "bybit":
                return await self._get_bybit_portfolio(connection_data)
            elif exchange == "bitmex":
                return await self._get_bitmex_portfolio(connection_data)
            elif exchange == "korea_investment":
                return await self._get_korea_investment_portfolio(connection_data)
            else:
                raise ValueError(f"Unsupported exchange: {exchange}")

        except Exception as e:
            self.log(f"Error fetching portfolio: {e}")
            return Data(
                data={
                    "status": "error",
                    "error": str(e),
                    "timestamp": int(time.time() * 1000),
                }
            )

    async def _get_binance_portfolio(self, connection_data: dict) -> Data:
        """Get portfolio from Binance."""
        base_url = connection_data.get("base_url")
        api_key = connection_data.get("api_key")
        api_secret = connection_data.get("api_secret")
        market_type = connection_data.get("market_type")

        async with httpx.AsyncClient() as client:
            timestamp = int(time.time() * 1000)
            headers = {"X-MBX-APIKEY": api_key}

            # Get account information
            if market_type == "spot":
                query_string = f"timestamp={timestamp}"
                signature = self._generate_signature(api_secret, query_string)
                account_url = f"{base_url}/api/v3/account?{query_string}&signature={signature}"
                account_response = await client.get(account_url, headers=headers)
                account_response.raise_for_status()
                account_info = account_response.json()

                # Process spot balances
                balances = [
                    {
                        "asset": b["asset"],
                        "free": float(b["free"]),
                        "locked": float(b["locked"]),
                        "total": float(b["free"]) + float(b["locked"]),
                    }
                    for b in account_info.get("balances", [])
                    if float(b["free"]) > 0 or float(b["locked"]) > 0
                ]

                total_balance = sum(
                    b["total"] for b in balances if b["asset"] == self.quote_currency
                )

                positions = []
                open_orders = []

            else:  # futures
                query_string = f"timestamp={timestamp}"
                signature = self._generate_signature(api_secret, query_string)

                # Get account balance
                balance_url = f"{base_url}/fapi/v2/balance?{query_string}&signature={signature}"
                balance_response = await client.get(balance_url, headers=headers)
                balance_response.raise_for_status()
                balance_info = balance_response.json()

                balances = [
                    {
                        "asset": b["asset"],
                        "free": float(b["availableBalance"]),
                        "locked": float(b["balance"]) - float(b["availableBalance"]),
                        "total": float(b["balance"]),
                    }
                    for b in balance_info
                    if float(b["balance"]) > 0
                ]

                total_balance = sum(
                    b["total"] for b in balances if b["asset"] == self.quote_currency
                )

                # Get positions
                positions = []
                if self.include_positions:
                    position_url = f"{base_url}/fapi/v2/positionRisk?{query_string}&signature={signature}"
                    position_response = await client.get(position_url, headers=headers)
                    position_response.raise_for_status()
                    position_info = position_response.json()

                    positions = [
                        {
                            "symbol": p["symbol"],
                            "side": "long" if float(p["positionAmt"]) > 0 else "short",
                            "size": abs(float(p["positionAmt"])),
                            "entry_price": float(p["entryPrice"]),
                            "mark_price": float(p["markPrice"]),
                            "liquidation_price": float(p["liquidationPrice"]),
                            "leverage": int(p["leverage"]),
                            "unrealized_pnl": float(p["unRealizedProfit"]),
                            "margin": float(p["isolatedMargin"])
                            if p["marginType"] == "isolated"
                            else 0,
                        }
                        for p in position_info
                        if float(p["positionAmt"]) != 0
                    ]

                # Get open orders
                open_orders = []
                if self.include_open_orders:
                    orders_url = f"{base_url}/fapi/v1/openOrders?{query_string}&signature={signature}"
                    orders_response = await client.get(orders_url, headers=headers)
                    orders_response.raise_for_status()
                    orders_info = orders_response.json()

                    open_orders = [
                        {
                            "order_id": o["orderId"],
                            "symbol": o["symbol"],
                            "side": o["side"].lower(),
                            "type": o["type"],
                            "price": float(o["price"]),
                            "quantity": float(o["origQty"]),
                            "filled": float(o["executedQty"]),
                            "status": o["status"],
                        }
                        for o in orders_info
                    ]

            # Calculate total PnL
            total_pnl = sum(p["unrealized_pnl"] for p in positions)

            # Calculate portfolio metrics
            total_margin_used = sum(p.get("margin", 0) for p in positions)
            total_position_value = sum(
                p["size"] * p["mark_price"] for p in positions if "mark_price" in p
            )

            result = {
                "status": "success",
                "exchange": "binance",
                "market_type": market_type,
                "quote_currency": self.quote_currency,
                "total_balance": total_balance,
                "available_balance": sum(b["free"] for b in balances),
                "locked_balance": sum(b["locked"] for b in balances),
                "balances": balances,
                "positions": positions,
                "open_orders": open_orders,
                "total_pnl": total_pnl,
                "total_margin_used": total_margin_used,
                "total_position_value": total_position_value,
                "margin_ratio": (total_margin_used / total_balance * 100) if total_balance > 0 else 0,
                "number_of_positions": len(positions),
                "number_of_orders": len(open_orders),
                "timestamp": int(time.time() * 1000),
            }

            self.log(
                f"Portfolio: Balance: {total_balance:.2f} {self.quote_currency}, "
                f"Positions: {len(positions)}, PnL: {total_pnl:.2f}"
            )

            return Data(data=result)

    async def _get_bybit_portfolio(self, connection_data: dict) -> Data:
        """Get portfolio from Bybit."""
        base_url = connection_data.get("base_url")
        api_key = connection_data.get("api_key")
        api_secret = connection_data.get("api_secret")
        market_type = connection_data.get("market_type")

        async with httpx.AsyncClient() as client:
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"

            # Get wallet balance
            balance_params = {"accountType": "UNIFIED"}
            param_str = f"{timestamp}{api_key}{recv_window}accountType={balance_params['accountType']}"
            signature = self._generate_signature(api_secret, param_str)

            headers = {
                "X-BAPI-API-KEY": api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": signature,
                "X-BAPI-RECV-WINDOW": recv_window,
            }

            balance_url = f"{base_url}/v5/account/wallet-balance"
            balance_response = await client.get(balance_url, headers=headers, params=balance_params)
            balance_response.raise_for_status()
            balance_result = balance_response.json()

            wallet = balance_result["result"]["list"][0] if balance_result["result"]["list"] else {}

            total_balance = float(wallet.get("totalEquity", 0))
            available_balance = float(wallet.get("totalAvailableBalance", 0))

            # Parse coin balances
            balances = [
                {
                    "asset": coin["coin"],
                    "total": float(coin.get("equity", 0)),
                    "available": float(coin.get("availableToWithdraw", 0)),
                    "locked": float(coin.get("locked", 0)),
                }
                for coin in wallet.get("coin", [])
                if float(coin.get("equity", 0)) > 0
            ]

            # Get positions
            positions = []
            if self.include_positions:
                timestamp = str(int(time.time() * 1000))
                position_params = {"category": market_type, "settleCoin": self.quote_currency}
                param_str = (
                    f"{timestamp}{api_key}{recv_window}"
                    f"category={position_params['category']}&settleCoin={position_params['settleCoin']}"
                )
                signature = self._generate_signature(api_secret, param_str)

                headers["X-BAPI-TIMESTAMP"] = timestamp
                headers["X-BAPI-SIGN"] = signature

                position_url = f"{base_url}/v5/position/list"
                position_response = await client.get(
                    position_url, headers=headers, params=position_params
                )
                position_response.raise_for_status()
                position_result = position_response.json()

                positions = [
                    {
                        "symbol": p["symbol"],
                        "side": p["side"].lower(),
                        "size": float(p["size"]),
                        "entry_price": float(p["avgPrice"]),
                        "mark_price": float(p["markPrice"]),
                        "liquidation_price": float(p["liqPrice"]) if p.get("liqPrice") else 0,
                        "leverage": float(p["leverage"]),
                        "unrealized_pnl": float(p["unrealisedPnl"]),
                        "realized_pnl": float(p["cumRealisedPnl"]),
                    }
                    for p in position_result["result"]["list"]
                    if float(p["size"]) > 0
                ]

            # Get open orders
            open_orders = []
            if self.include_open_orders:
                timestamp = str(int(time.time() * 1000))
                order_params = {"category": market_type}
                param_str = f"{timestamp}{api_key}{recv_window}category={order_params['category']}"
                signature = self._generate_signature(api_secret, param_str)

                headers["X-BAPI-TIMESTAMP"] = timestamp
                headers["X-BAPI-SIGN"] = signature

                orders_url = f"{base_url}/v5/order/realtime"
                orders_response = await client.get(orders_url, headers=headers, params=order_params)
                orders_response.raise_for_status()
                orders_result = orders_response.json()

                open_orders = [
                    {
                        "order_id": o["orderId"],
                        "symbol": o["symbol"],
                        "side": o["side"].lower(),
                        "type": o["orderType"],
                        "price": float(o["price"]),
                        "quantity": float(o["qty"]),
                        "filled": float(o.get("cumExecQty", 0)),
                        "status": o["orderStatus"],
                    }
                    for o in orders_result["result"]["list"]
                ]

            total_pnl = sum(p["unrealized_pnl"] for p in positions)
            total_position_value = sum(p["size"] * p["mark_price"] for p in positions)

            result = {
                "status": "success",
                "exchange": "bybit",
                "market_type": market_type,
                "quote_currency": self.quote_currency,
                "total_balance": total_balance,
                "available_balance": available_balance,
                "locked_balance": total_balance - available_balance,
                "balances": balances,
                "positions": positions,
                "open_orders": open_orders,
                "total_pnl": total_pnl,
                "total_position_value": total_position_value,
                "number_of_positions": len(positions),
                "number_of_orders": len(open_orders),
                "timestamp": int(time.time() * 1000),
            }

            self.log(
                f"Portfolio: Balance: {total_balance:.2f}, Positions: {len(positions)}, PnL: {total_pnl:.2f}"
            )

            return Data(data=result)

    async def _get_bitmex_portfolio(self, connection_data: dict) -> Data:
        """Get portfolio from BitMEX."""
        base_url = connection_data.get("base_url")
        api_key = connection_data.get("api_key")
        api_secret = connection_data.get("api_secret")

        async with httpx.AsyncClient() as client:
            verb = "GET"
            expires = int(time.time()) + 60

            # Get user margin
            path = "/api/v1/user/margin"
            message = f"{verb}{path}{expires}"
            signature = hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()

            headers = {
                "api-expires": str(expires),
                "api-key": api_key,
                "api-signature": signature,
            }

            margin_url = f"{base_url}{path}"
            margin_response = await client.get(margin_url, headers=headers)
            margin_response.raise_for_status()
            margin_info = margin_response.json()

            # Balance in satoshis, convert to BTC
            total_balance = margin_info.get("walletBalance", 0) / 100000000
            available_balance = margin_info.get("availableMargin", 0) / 100000000

            balances = [{"asset": "BTC", "total": total_balance, "available": available_balance}]

            # Get positions
            positions = []
            if self.include_positions:
                expires = int(time.time()) + 60
                path = "/api/v1/position"
                message = f"{verb}{path}{expires}"
                signature = hmac.new(
                    api_secret.encode(), message.encode(), hashlib.sha256
                ).hexdigest()

                headers["api-expires"] = str(expires)
                headers["api-signature"] = signature

                position_url = f"{base_url}{path}"
                position_response = await client.get(position_url, headers=headers)
                position_response.raise_for_status()
                position_info = position_response.json()

                positions = [
                    {
                        "symbol": p["symbol"],
                        "side": "long" if p["currentQty"] > 0 else "short",
                        "size": abs(p["currentQty"]),
                        "entry_price": p.get("avgEntryPrice", 0),
                        "mark_price": p.get("markPrice", 0),
                        "liquidation_price": p.get("liquidationPrice", 0),
                        "leverage": p.get("leverage", 1),
                        "unrealized_pnl": p.get("unrealisedPnl", 0) / 100000000,
                        "realized_pnl": p.get("realisedPnl", 0) / 100000000,
                    }
                    for p in position_info
                    if p.get("currentQty", 0) != 0
                ]

            # Get open orders
            open_orders = []
            if self.include_open_orders:
                expires = int(time.time()) + 60
                path = "/api/v1/order"
                query = "?filter=%7B%22open%22%3Atrue%7D"  # filter={"open":true}
                message = f"{verb}{path}{query}{expires}"
                signature = hmac.new(
                    api_secret.encode(), message.encode(), hashlib.sha256
                ).hexdigest()

                headers["api-expires"] = str(expires)
                headers["api-signature"] = signature

                orders_url = f"{base_url}{path}{query}"
                orders_response = await client.get(orders_url, headers=headers)
                orders_response.raise_for_status()
                orders_info = orders_response.json()

                open_orders = [
                    {
                        "order_id": o["orderID"],
                        "symbol": o["symbol"],
                        "side": o["side"].lower(),
                        "type": o["ordType"],
                        "price": o.get("price", 0),
                        "quantity": o["orderQty"],
                        "filled": o.get("cumQty", 0),
                        "status": o["ordStatus"],
                    }
                    for o in orders_info
                ]

            total_pnl = sum(p["unrealized_pnl"] for p in positions)

            result = {
                "status": "success",
                "exchange": "bitmex",
                "quote_currency": "BTC",
                "total_balance": total_balance,
                "available_balance": available_balance,
                "balances": balances,
                "positions": positions,
                "open_orders": open_orders,
                "total_pnl": total_pnl,
                "number_of_positions": len(positions),
                "number_of_orders": len(open_orders),
                "timestamp": int(time.time() * 1000),
            }

            self.log(
                f"Portfolio: Balance: {total_balance:.8f} BTC, Positions: {len(positions)}, PnL: {total_pnl:.8f} BTC"
            )

            return Data(data=result)

    async def _get_korea_investment_portfolio(self, connection_data: dict) -> Data:
        """Get portfolio from Korea Investment & Securities."""
        base_url = connection_data.get("base_url")
        access_token = connection_data.get("access_token")
        app_key = connection_data.get("app_key")
        app_secret = connection_data.get("app_secret")
        account_number = connection_data.get("account_number")
        environment = connection_data.get("environment")

        async with httpx.AsyncClient() as client:
            # Get account balance
            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {access_token}",
                "appkey": app_key,
                "appsecret": app_secret,
                "tr_id": "TTTC8434R" if environment == "virtual" else "CTTC8434R",
            }

            balance_url = f"{base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
            params = {
                "CANO": account_number.split("-")[0],
                "ACNT_PRDT_CD": account_number.split("-")[1],
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "N",
                "INQR_DVSN": "01",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "00",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            }

            balance_response = await client.get(balance_url, headers=headers, params=params)
            balance_response.raise_for_status()
            balance_result = balance_response.json()

            output1 = balance_result.get("output1", [])
            output2 = balance_result.get("output2", [{}])[0]

            # Get positions (stocks)
            positions = [
                {
                    "symbol": stock["pdno"],
                    "name": stock.get("prdt_name", ""),
                    "quantity": int(stock.get("hldg_qty", 0)),
                    "entry_price": float(stock.get("pchs_avg_pric", 0)),
                    "current_price": float(stock.get("prpr", 0)),
                    "eval_amount": float(stock.get("evlu_amt", 0)),
                    "pnl": float(stock.get("evlu_pfls_amt", 0)),
                    "pnl_rate": float(stock.get("evlu_pfls_rt", 0)),
                }
                for stock in output1
            ]

            # Account summary
            total_balance = float(output2.get("tot_evlu_amt", 0))
            available_balance = float(output2.get("nass_amt", 0))
            total_pnl = float(output2.get("evlu_pfls_smtl_amt", 0))

            result = {
                "status": "success",
                "exchange": "korea_investment",
                "quote_currency": "KRW",
                "total_balance": total_balance,
                "available_balance": available_balance,
                "positions": positions,
                "total_pnl": total_pnl,
                "number_of_positions": len(positions),
                "timestamp": int(time.time() * 1000),
            }

            self.log(
                f"Portfolio: Balance: ₩{total_balance:,.0f}, Positions: {len(positions)}, PnL: ₩{total_pnl:,.0f}"
            )

            return Data(data=result)

    def build(self):
        return self.get_portfolio
