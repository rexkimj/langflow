"""Exchange API connector components for various trading platforms."""

import asyncio
import hashlib
import hmac
import time
from typing import Any

import httpx
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, Output, SecretStrInput, StrInput
from lfx.schema.data import Data


class BaseExchangeConnector(Component):
    """Base class for exchange connectors."""

    def _generate_signature(self, secret: str, message: str) -> str:
        """Generate HMAC signature for API authentication."""
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    def _handle_error(self, error: Exception) -> Data:
        """Handle and format errors."""
        error_msg = str(error)
        self.log(f"Error: {error_msg}")
        return Data(
            data={
                "status": "error",
                "error": error_msg,
                "timestamp": int(time.time() * 1000),
            }
        )


class BinanceConnector(BaseExchangeConnector):
    """Binance exchange API connector for spot and futures trading."""

    display_name = "Binance Connector"
    description = "Connect to Binance exchange API for trading and market data"
    icon = "TrendingUp"
    name = "BinanceConnector"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            required=True,
            info="Binance API key",
        ),
        SecretStrInput(
            name="api_secret",
            display_name="API Secret",
            required=True,
            info="Binance API secret",
        ),
        DropdownInput(
            name="market_type",
            display_name="Market Type",
            options=["spot", "futures"],
            value="spot",
            info="Trading market type",
        ),
        BoolInput(
            name="testnet",
            display_name="Use Testnet",
            value=True,
            info="Use testnet for testing",
        ),
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=30,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Connection",
            name="connection",
            method="connect",
        ),
    ]

    async def connect(self) -> Data:
        """Establish connection to Binance API."""
        try:
            # Determine base URL
            if self.testnet:
                base_url = (
                    "https://testnet.binance.vision"
                    if self.market_type == "spot"
                    else "https://testnet.binancefuture.com"
                )
            else:
                base_url = (
                    "https://api.binance.com"
                    if self.market_type == "spot"
                    else "https://fapi.binance.com"
                )

            # Test connection with account info
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                timestamp = int(time.time() * 1000)
                query_string = f"timestamp={timestamp}"
                signature = self._generate_signature(self.api_secret, query_string)

                headers = {"X-MBX-APIKEY": self.api_key}
                url = f"{base_url}/api/v3/account?{query_string}&signature={signature}"

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                account_info = response.json()

                self.log("Successfully connected to Binance")
                return Data(
                    data={
                        "status": "connected",
                        "exchange": "binance",
                        "market_type": self.market_type,
                        "testnet": self.testnet,
                        "base_url": base_url,
                        "api_key": self.api_key,
                        "api_secret": self.api_secret,
                        "balances": account_info.get("balances", []),
                        "timestamp": timestamp,
                    }
                )

        except Exception as e:
            return self._handle_error(e)

    def build(self):
        return self.connect


class BybitConnector(BaseExchangeConnector):
    """Bybit exchange API connector for derivatives trading."""

    display_name = "Bybit Connector"
    description = "Connect to Bybit exchange API for derivatives trading"
    icon = "TrendingUp"
    name = "BybitConnector"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            required=True,
            info="Bybit API key",
        ),
        SecretStrInput(
            name="api_secret",
            display_name="API Secret",
            required=True,
            info="Bybit API secret",
        ),
        DropdownInput(
            name="market_type",
            display_name="Market Type",
            options=["spot", "linear", "inverse"],
            value="linear",
            info="Market type: spot, linear (USDT perpetual), inverse (coin perpetual)",
        ),
        BoolInput(
            name="testnet",
            display_name="Use Testnet",
            value=True,
            info="Use testnet for testing",
        ),
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=30,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Connection",
            name="connection",
            method="connect",
        ),
    ]

    async def connect(self) -> Data:
        """Establish connection to Bybit API."""
        try:
            # Determine base URL
            if self.testnet:
                base_url = "https://api-testnet.bybit.com"
            else:
                base_url = "https://api.bybit.com"

            # Test connection with account info
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                timestamp = str(int(time.time() * 1000))
                recv_window = "5000"

                # Create signature
                param_str = f"api_key={self.api_key}&timestamp={timestamp}&recv_window={recv_window}"
                signature = self._generate_signature(self.api_secret, param_str)

                headers = {
                    "X-BAPI-API-KEY": self.api_key,
                    "X-BAPI-TIMESTAMP": timestamp,
                    "X-BAPI-SIGN": signature,
                    "X-BAPI-RECV-WINDOW": recv_window,
                }

                # Get wallet balance
                url = f"{base_url}/v5/account/wallet-balance"
                params = {"accountType": "UNIFIED"}

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()

                result = response.json()

                self.log("Successfully connected to Bybit")
                return Data(
                    data={
                        "status": "connected",
                        "exchange": "bybit",
                        "market_type": self.market_type,
                        "testnet": self.testnet,
                        "base_url": base_url,
                        "api_key": self.api_key,
                        "api_secret": self.api_secret,
                        "account_info": result.get("result", {}),
                        "timestamp": timestamp,
                    }
                )

        except Exception as e:
            return self._handle_error(e)

    def build(self):
        return self.connect


class BitmexConnector(BaseExchangeConnector):
    """BitMEX exchange API connector for derivatives trading."""

    display_name = "BitMEX Connector"
    description = "Connect to BitMEX exchange API for derivatives trading"
    icon = "TrendingUp"
    name = "BitmexConnector"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            required=True,
            info="BitMEX API key",
        ),
        SecretStrInput(
            name="api_secret",
            display_name="API Secret",
            required=True,
            info="BitMEX API secret",
        ),
        BoolInput(
            name="testnet",
            display_name="Use Testnet",
            value=True,
            info="Use testnet for testing",
        ),
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=30,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Connection",
            name="connection",
            method="connect",
        ),
    ]

    async def connect(self) -> Data:
        """Establish connection to BitMEX API."""
        try:
            # Determine base URL
            base_url = "https://testnet.bitmex.com" if self.testnet else "https://www.bitmex.com"

            # Test connection with user info
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                verb = "GET"
                path = "/api/v1/user"
                expires = int(time.time()) + 60

                # Create signature
                message = f"{verb}{path}{expires}"
                signature = hmac.new(
                    self.api_secret.encode(), message.encode(), hashlib.sha256
                ).hexdigest()

                headers = {
                    "api-expires": str(expires),
                    "api-key": self.api_key,
                    "api-signature": signature,
                }

                url = f"{base_url}{path}"
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                user_info = response.json()

                self.log("Successfully connected to BitMEX")
                return Data(
                    data={
                        "status": "connected",
                        "exchange": "bitmex",
                        "testnet": self.testnet,
                        "base_url": base_url,
                        "api_key": self.api_key,
                        "api_secret": self.api_secret,
                        "user_info": user_info,
                        "timestamp": int(time.time() * 1000),
                    }
                )

        except Exception as e:
            return self._handle_error(e)

    def build(self):
        return self.connect


class KoreaInvestmentConnector(BaseExchangeConnector):
    """Korea Investment & Securities API connector for Korean stock trading."""

    display_name = "Korea Investment Connector"
    description = "Connect to Korea Investment & Securities API for Korean stock trading"
    icon = "TrendingUp"
    name = "KoreaInvestmentConnector"

    inputs = [
        SecretStrInput(
            name="app_key",
            display_name="App Key",
            required=True,
            info="Korea Investment App Key",
        ),
        SecretStrInput(
            name="app_secret",
            display_name="App Secret",
            required=True,
            info="Korea Investment App Secret",
        ),
        StrInput(
            name="account_number",
            display_name="Account Number",
            required=True,
            info="Trading account number",
        ),
        DropdownInput(
            name="environment",
            display_name="Environment",
            options=["real", "virtual"],
            value="virtual",
            info="Trading environment",
        ),
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=30,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Connection",
            name="connection",
            method="connect",
        ),
    ]

    async def connect(self) -> Data:
        """Establish connection to Korea Investment API."""
        try:
            # Determine base URL
            if self.environment == "virtual":
                base_url = "https://openapivts.koreainvestment.com:29443"
            else:
                base_url = "https://openapi.koreainvestment.com:9443"

            # Get access token
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                token_url = f"{base_url}/oauth2/tokenP"
                token_data = {
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                }

                token_response = await client.post(token_url, json=token_data)
                token_response.raise_for_status()

                token_result = token_response.json()
                access_token = token_result.get("access_token")

                if not access_token:
                    raise ValueError("Failed to obtain access token")

                # Test with account balance inquiry
                headers = {
                    "content-type": "application/json; charset=utf-8",
                    "authorization": f"Bearer {access_token}",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                    "tr_id": "TTTC8434R" if self.environment == "virtual" else "CTTC8434R",
                }

                balance_url = f"{base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
                params = {
                    "CANO": self.account_number.split("-")[0],
                    "ACNT_PRDT_CD": self.account_number.split("-")[1],
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

                self.log("Successfully connected to Korea Investment & Securities")
                return Data(
                    data={
                        "status": "connected",
                        "exchange": "korea_investment",
                        "environment": self.environment,
                        "base_url": base_url,
                        "access_token": access_token,
                        "app_key": self.app_key,
                        "app_secret": self.app_secret,
                        "account_number": self.account_number,
                        "balance_info": balance_result,
                        "timestamp": int(time.time() * 1000),
                    }
                )

        except Exception as e:
            return self._handle_error(e)

    def build(self):
        return self.connect
