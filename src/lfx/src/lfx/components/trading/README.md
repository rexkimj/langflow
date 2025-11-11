# Trading Components for Langflow

## 개요 (Overview)

Langflow를 위한 전문적인 비주얼 노드 기반 자동 매매 시스템 컴포넌트입니다. 다양한 거래소 API와 연동하여 실시간 시세 조회, 주문 실행, 리스크 관리, 포트폴리오 추적, AI 기반 의사결정을 지원합니다.

Professional visual node-based automated trading system components for Langflow. Supports multiple exchange APIs with real-time market data, order execution, risk management, portfolio tracking, and AI-powered decision making.

## 주요 기능 (Key Features)

### 🔌 거래소 연동 (Exchange Connectors)
- **Binance** (바이낸스): Spot & Futures trading
- **Bybit** (바이비트): Spot, Linear, Inverse derivatives
- **BitMEX** (비트멕스): Derivatives trading
- **Korea Investment** (한국투자증권): Korean stock trading

### 📊 시장 데이터 (Market Data)
- **Price Feed**: Real-time price updates with multiple intervals
- **Order Book**: Market depth analysis with imbalance calculation
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Moving Averages

### 💰 주문 실행 (Trading Execution)
- Market, Limit, Stop Loss, Take Profit orders
- Long/Short positions with leverage support (1x-125x)
- Reduce-only and Post-only options
- Test mode for safe testing

### 🛡️ 리스크 관리 (Risk Management)
- **Stop Loss Manager**: Automatic stop-loss with trailing stop
- **Risk Analyzer**: Position sizing, leverage analysis, risk warnings
- Real-time risk metrics and liquidation price calculation
- ATR-based dynamic stop loss

### 💼 포트폴리오 관리 (Portfolio Management)
- Real-time balance and position tracking
- Open orders monitoring
- PnL calculation (realized & unrealized)
- Multi-asset portfolio support

### 🤖 AI 트레이딩 에이전트 (AI Trading Agent)
- LLM-powered market analysis
- Technical indicator integration
- Rule-based fallback system
- Confidence-based decision making

### 📈 성과 리포트 (Performance Reporting)
- Comprehensive performance metrics
- Win rate, profit factor, Sharpe ratio
- Risk metrics and drawdown analysis
- Visual chart data generation

## 설치 및 설정 (Installation & Setup)

### 1. 컴포넌트 위치
```
/home/user/langflow/src/lfx/src/lfx/components/trading/
├── __init__.py
├── exchange_connectors.py
├── market_data.py
├── trading_execution.py
├── risk_management.py
├── portfolio_management.py
├── ai_trading_agent.py
└── performance_report.py
```

### 2. 필요한 의존성
```bash
pip install httpx langchain langchain-openai langchain-anthropic
```

### 3. API 키 설정
각 거래소의 API 키를 안전하게 보관하고 컴포넌트에 입력하세요.

## 사용 방법 (Usage)

### 기본 트레이딩 플로우 (Basic Trading Flow)

```
1. Exchange Connector → 2. Price Feed → 3. AI Trading Agent → 4. Risk Analyzer → 5. Order Executor
                         ↓
                    Portfolio Manager → Performance Reporter
```

### 예제 1: 바이낸스 자동 매매 (Binance Automated Trading)

**플로우 구성:**
1. **Binance Connector**
   - API Key: [Your API Key]
   - API Secret: [Your API Secret]
   - Market Type: futures
   - Use Testnet: ✓

2. **Price Feed**
   - Exchange Connection: [From Binance Connector]
   - Symbol: BTCUSDT
   - Interval: 5m
   - Include Order Book: ✓

3. **Portfolio Manager**
   - Exchange Connection: [From Binance Connector]
   - Calculate PnL: ✓

4. **AI Trading Agent**
   - Price Data: [From Price Feed]
   - Portfolio Data: [From Portfolio Manager]
   - LLM: [OpenAI GPT-4 or Claude]
   - Trading Strategy: "Analyze Bitcoin price and provide conservative trading signals"
   - Confidence Threshold: 0.75

5. **Risk Analyzer**
   - Price Data: [From Price Feed]
   - Portfolio Data: [From Portfolio Manager]
   - Max Risk Per Trade: 2%
   - Max Leverage: 10x

6. **Order Executor**
   - Exchange Connection: [From Binance Connector]
   - Symbol: BTCUSDT
   - Side: [From AI Trading Agent decision]
   - Order Type: market
   - Quantity: [Calculated from Risk Analyzer]
   - Leverage: 5x
   - Test Mode: ✓ (처음에는 반드시 테스트 모드!)

7. **Performance Reporter**
   - Portfolio Data: [From Portfolio Manager]
   - Initial Balance: 10000
   - Report Period: all_time

### 예제 2: 한국 주식 자동 매매 (Korean Stock Trading)

**플로우 구성:**
1. **Korea Investment Connector**
   - App Key: [Your App Key]
   - App Secret: [Your App Secret]
   - Account Number: [Your Account]
   - Environment: virtual

2. **Price Feed**
   - Exchange Connection: [From Korea Investment]
   - Symbol: 005930 (삼성전자)
   - Interval: 1m

3. **Order Executor**
   - Symbol: 005930
   - Side: buy
   - Order Type: limit
   - Quantity: 10
   - Price: [Current Price - 100]
   - Test Mode: ✓

### 예제 3: 리스크 관리 중심 플로우 (Risk-Focused Flow)

```
Exchange Connector → Price Feed → Stop Loss Manager
                                        ↓
                    Risk Analyzer → [Decision: Execute or Hold]
                                        ↓
                    Order Executor (if safe to trade)
```

## 컴포넌트 상세 설명 (Component Details)

### 1. Exchange Connectors

#### BinanceConnector
- **입력**: API Key, API Secret, Market Type, Testnet
- **출력**: Connection object with authentication
- **용도**: 바이낸스 거래소 연결

#### BybitConnector
- **입력**: API Key, API Secret, Market Type, Testnet
- **출력**: Connection object
- **용도**: 바이비트 거래소 연결

#### BitmexConnector
- **입력**: API Key, API Secret, Testnet
- **출력**: Connection object
- **용도**: 비트멕스 거래소 연결

#### KoreaInvestmentConnector
- **입력**: App Key, App Secret, Account Number, Environment
- **출력**: Connection object with access token
- **용도**: 한국투자증권 API 연결

### 2. Market Data

#### PriceFeed
- **입력**: Exchange Connection, Symbol, Interval, Historical Candles
- **출력**: Real-time price data with technical indicators
- **기능**:
  - Current price, 24h change, volume
  - Historical candlestick data
  - Order book (optional)
  - Automatic interval conversion per exchange

#### OrderBook
- **입력**: Exchange Connection, Symbol, Depth Level
- **출력**: Bid/Ask order book with metrics
- **기능**:
  - Market depth visualization
  - Spread calculation
  - Order book imbalance ratio

### 3. Trading Execution

#### OrderExecutor
- **입력**: Exchange Connection, Symbol, Side, Order Type, Quantity, Price, Leverage
- **출력**: Order execution result
- **기능**:
  - Multiple order types (market, limit, stop loss, take profit)
  - Long/Short position support
  - Leverage setting (1x-125x)
  - Test mode for safety
  - Reduce-only and Post-only options

### 4. Risk Management

#### StopLossManager
- **입력**: Price Data, Entry Price, Position Side, Stop Loss %, Take Profit %
- **출력**: Stop loss triggers and risk metrics
- **기능**:
  - Basic stop loss and take profit
  - Trailing stop loss
  - ATR-based dynamic stop loss
  - Risk/reward ratio calculation

#### RiskAnalyzer
- **입력**: Price Data, Portfolio Data, Position Size, Entry Price, Stop Loss Price, Leverage
- **출력**: Risk analysis with warnings
- **기능**:
  - Position size validation
  - Leverage risk assessment
  - Liquidation price calculation
  - Risk warnings generation
  - Optimal position size recommendation

### 5. Portfolio Management

#### PortfolioManager
- **입력**: Exchange Connection, Include Options
- **출력**: Complete portfolio snapshot
- **기능**:
  - Account balance tracking
  - Open positions monitoring
  - Open orders tracking
  - PnL calculation
  - Multi-exchange support

### 6. AI Trading Agent

#### TradingAIAgent
- **입력**: Price Data, Portfolio Data, Risk Analysis, LLM, Trading Strategy
- **출력**: Trading decision with confidence score
- **기능**:
  - LLM-powered market analysis
  - Technical indicator integration
  - Confidence-based filtering
  - Rule-based fallback
  - Detailed reasoning

### 7. Performance Reporting

#### PerformanceReporter
- **입력**: Portfolio Data, Initial Balance, Report Period
- **출력**: Comprehensive performance report
- **기능**:
  - Total return calculation
  - Win rate and profit factor
  - Sharpe ratio
  - Maximum drawdown
  - Risk metrics
  - Chart data generation

## 보안 주의사항 (Security Notes)

### ⚠️ 중요 (Important)

1. **API 키 보안**
   - API 키를 코드에 하드코딩하지 마세요
   - 환경 변수나 시크릿 매니저를 사용하세요
   - 읽기 전용 API 키를 가능한 사용하세요

2. **테스트 모드**
   - 실제 자금을 사용하기 전에 반드시 테스트넷에서 테스트하세요
   - Test Mode를 활성화하여 주문 시뮬레이션을 먼저 해보세요

3. **리스크 관리**
   - 레버리지는 신중하게 사용하세요
   - 항상 스탑로스를 설정하세요
   - 포트폴리오의 2-5% 이상 리스크를 지지 마세요

4. **API 권한**
   - 거래 권한만 최소한으로 부여하세요
   - 출금 권한은 API 키에 부여하지 마세요

## 트러블슈팅 (Troubleshooting)

### 연결 오류 (Connection Errors)
```
Error: Failed to connect to exchange
Solution: API 키와 시크릿을 확인하세요. 테스트넷 설정을 확인하세요.
```

### 주문 실패 (Order Failures)
```
Error: Insufficient balance
Solution: 계좌 잔액을 확인하세요. 포트폴리오 매니저로 현재 잔액을 확인할 수 있습니다.
```

### 서명 오류 (Signature Errors)
```
Error: Invalid signature
Solution: API Secret이 올바른지 확인하세요. 시스템 시간이 동기화되어 있는지 확인하세요.
```

## 라이선스 (License)

이 컴포넌트는 Langflow 프로젝트의 일부로 개발되었습니다.

## 면책 조항 (Disclaimer)

⚠️ **경고**: 이 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 실제 자금을 사용한 거래는 상당한 금전적 손실 위험이 있습니다. 사용자는 모든 거래 결정에 대한 전적인 책임을 집니다. 개발자는 이 소프트웨어의 사용으로 인한 어떠한 금전적 손실에 대해서도 책임지지 않습니다.

**WARNING**: This software is provided for educational and research purposes only. Trading with real funds carries substantial risk of financial loss. Users are solely responsible for all trading decisions. The developers are not liable for any financial losses resulting from the use of this software.

## 기여 (Contributing)

버그 리포트, 기능 제안, PR을 환영합니다!

## 문의 (Contact)

이슈나 질문이 있으시면 GitHub Issues를 이용해주세요.
