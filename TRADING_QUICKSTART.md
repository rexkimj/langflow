# 🚀 Langflow 트레이딩 시스템 빠른 시작 가이드

## 실행 방법

### 1. Langflow 서버 시작

```bash
# 터미널에서 실행
cd /home/user/langflow
langflow run --host 0.0.0.0 --port 7860
```

서버가 시작되면 다음과 같은 메시지가 나타납니다:
```
╭─────────────────────────────────────────────────╮
│ Welcome to ⛓ Langflow                          │
│                                                 │
│ Access http://127.0.0.1:7860                   │
╰─────────────────────────────────────────────────╯
```

### 2. 웹 브라우저 열기

브라우저에서 `http://localhost:7860` 접속

---

## 📋 예제 1: 바이낸스 가격 조회 (가장 간단)

### 단계별 가이드:

1. **New Flow** 클릭 → 빈 캔버스

2. **왼쪽 사이드바**에서 컴포넌트 찾기:
   - 검색창에 "Binance" 입력
   - **Binance Connector** 클릭하여 추가

3. **Binance Connector 설정**:
   - API Key: `your_api_key` (테스트용)
   - API Secret: `your_api_secret`
   - Market Type: `spot`
   - **Use Testnet: ✅ 체크 (중요!)**
   - Timeout: `30`

4. **Price Feed 추가**:
   - 검색: "Price Feed"
   - 캔버스에 드래그

5. **Price Feed 설정**:
   - Symbol: `BTCUSDT`
   - Interval: `5m`
   - Historical Candles: `100`
   - Include Order Book: ✅

6. **컴포넌트 연결**:
   - Binance Connector의 **"Connection"** 출력 → Price Feed의 **"Exchange Connection"** 입력으로 드래그

7. **실행**:
   - Price Feed 노드의 ▶️ **Run** 버튼 클릭
   - 결과 확인!

### 예상 출력:

```json
{
  "status": "success",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "current_price": 43250.50,
  "price_change_24h": 1250.30,
  "price_change_percent_24h": 2.98,
  "high_24h": 43800.00,
  "low_24h": 41500.00,
  "volume_24h": 15234.56,
  "candles": [...],
  "technical_indicators": {
    "rsi_14": 65.5,
    "sma_20": 42800.25,
    "bb_upper": 44000.00,
    "bb_lower": 41600.00
  }
}
```

---

## 📋 예제 2: AI 트레이딩 의사결정 (중급)

### 플로우 구성:

```
[Binance Connector] → [Price Feed] ──┐
                                      ├→ [Trading AI Agent] → [결과]
[Portfolio Manager] ─────────────────┘
          ↑
[Binance Connector]
```

### 단계:

1. **Binance Connector** (위와 동일)

2. **Price Feed** 추가 및 연결

3. **Portfolio Manager** 추가:
   - Exchange Connection: Binance Connector의 출력
   - Include Open Orders: ✅
   - Include Positions: ✅
   - Calculate PnL: ✅

4. **OpenAI** 컴포넌트 추가 (Models 카테고리):
   - Model: `gpt-4`
   - API Key: `your_openai_api_key`

5. **Trading AI Agent** 추가:
   - Price Data: Price Feed 출력
   - Portfolio Data: Portfolio Manager 출력
   - LLM: OpenAI 모델
   - Trading Strategy: `"비트코인 가격을 분석하고 보수적인 매매 신호를 제공하세요"`
   - Confidence Threshold: `0.75`

6. **실행** → AI가 매수/매도/대기 결정!

### 예상 AI 결정:

```json
{
  "status": "success",
  "action": "buy",
  "confidence": 0.82,
  "reasoning": "RSI가 45로 과매도 구간에 진입했고, 가격이 볼린저밴드 하단을 터치했습니다.
               SMA20이 상승 추세를 보이고 있어 매수 진입 시점으로 판단됩니다.",
  "entry_price": 43250.50,
  "target_price": 44500.00,
  "stop_loss_price": 42500.00,
  "position_size": 5,
  "risk_reward_ratio": 2.5
}
```

---

## 📋 예제 3: 완전 자동 매매 시스템 (고급)

### 전체 플로우:

```
┌─────────────────┐
│ 1. Exchange     │
│    Connector    │
└────┬────────┬───┘
     │        │
     ▼        ▼
┌─────────┐ ┌──────────┐
│ 2. Price│ │ 3. Port- │
│    Feed │ │   folio  │
└────┬────┘ └────┬─────┘
     │           │
     └─────┬─────┘
           ▼
      ┌─────────────┐
      │ 4. AI Agent │
      └─────┬───────┘
            ▼
      ┌──────────────┐
      │ 5. Risk      │
      │    Analyzer  │
      └─────┬────────┘
            ▼
      ┌──────────────┐
      │ 6. Stop Loss │
      │    Manager   │
      └─────┬────────┘
            ▼
      ┌──────────────┐
      │ 7. Order     │
      │    Executor  │
      └─────┬────────┘
            ▼
      ┌──────────────┐
      │ 8. Performance│
      │    Reporter  │
      └──────────────┘
```

### 컴포넌트별 설정:

#### 1. Binance Connector
```
API Key: [Your Key]
API Secret: [Your Secret]
Market Type: futures
Use Testnet: ✅ (처음엔 필수!)
```

#### 2. Price Feed
```
Symbol: BTCUSDT
Interval: 5m
Include Order Book: ✅
```

#### 3. Portfolio Manager
```
Calculate PnL: ✅
Include Positions: ✅
```

#### 4. Trading AI Agent
```
LLM: OpenAI GPT-4
Trading Strategy: "기술적 분석과 리스크 관리 원칙에 따라 트레이딩하세요"
Confidence Threshold: 0.75
Auto Execute: ❌ (처음엔 수동!)
```

#### 5. Risk Analyzer
```
Position Size: [AI Agent의 권장 사이즈]
Max Risk Per Trade: 2%
Max Leverage: 5x
```

#### 6. Stop Loss Manager
```
Entry Price: [AI Agent의 진입가]
Position Side: long/short
Stop Loss %: 2%
Take Profit %: 5%
Use Trailing Stop: ✅
```

#### 7. Order Executor
```
Symbol: BTCUSDT
Side: [AI Agent 결정]
Order Type: market
Leverage: 3x
Test Mode: ✅ (처음엔 필수!)
```

#### 8. Performance Reporter
```
Initial Balance: 10000
Report Period: all_time
Include Detailed Metrics: ✅
```

---

## 🎯 테스트 시나리오

### 시나리오 1: 가격만 확인
```
Binance Connector (Testnet) → Price Feed → 실행
```
**목적**: 시스템이 정상 작동하는지 확인

### 시나리오 2: AI 의견 듣기
```
Price Feed + Portfolio → AI Agent → 실행
```
**목적**: AI가 어떤 판단을 내리는지 확인

### 시나리오 3: 리스크 체크
```
AI Agent → Risk Analyzer → 실행
```
**목적**: 리스크 경고가 제대로 나오는지 확인

### 시나리오 4: 테스트 주문
```
전체 플로우 + Test Mode ✅ → 실행
```
**목적**: 실제 주문 없이 시뮬레이션

### 시나리오 5: 실전 (신중히!)
```
전체 플로우 + Test Mode ❌ + 소액 → 실행
```
**목적**: 실제 매매 (충분히 테스트 후!)

---

## ⚠️ 안전 수칙

### 반드시 지켜야 할 것:

1. **테스트넷부터 시작**
   ```
   Use Testnet: ✅ (모든 거래소 커넥터)
   ```

2. **테스트 모드 활성화**
   ```
   Test Mode: ✅ (Order Executor)
   ```

3. **소액으로 시작**
   - 처음엔 최소 금액 (예: $10-$50)
   - 시스템 검증 후 점진적 확대

4. **항상 스탑로스 설정**
   ```
   Stop Loss Manager 반드시 사용
   ```

5. **레버리지 조심**
   ```
   처음엔 1x (무레버리지)
   익숙해지면 2-3x
   절대 10x 이상 사용 금지
   ```

6. **API 키 권한 최소화**
   - 읽기 + 거래만 허용
   - 출금 권한 절대 부여 금지

---

## 🔧 트러블슈팅

### Q1: "Connection failed" 에러
**A**: API 키/시크릿 확인, 테스트넷 설정 확인

### Q2: 컴포넌트가 안 보여요
**A**:
```bash
# Langflow 재시작
pkill -f langflow
langflow run --host 0.0.0.0 --port 7860
```

### Q3: "Insufficient balance" 에러
**A**: Portfolio Manager로 잔액 확인

### Q4: AI가 결정을 안 내려요
**A**:
- Confidence Threshold 낮추기 (0.5로)
- LLM API 키 확인
- 프롬프트 단순화

### Q5: 주문이 실행 안돼요
**A**:
- Test Mode 확인
- 거래소 API 권한 확인
- 레버리지 설정 확인

---

## 📚 더 알아보기

### 한국투자증권으로 국내주식 매매:

```
Korea Investment Connector:
  App Key: [앱 키]
  App Secret: [앱 시크릿]
  Account Number: 12345678-01
  Environment: virtual (모의투자)

Price Feed:
  Symbol: 005930 (삼성전자)

Order Executor:
  Symbol: 005930
  Side: buy
  Quantity: 10
  Order Type: limit
  Price: 70000
  Test Mode: ✅
```

### 바이비트 선물 거래:

```
Bybit Connector:
  Market Type: linear (USDT 선물)

Price Feed:
  Symbol: BTCUSDT

Order Executor:
  Position Side: long
  Leverage: 3x
```

---

## 💡 Pro Tips

1. **로그 확인하기**: 각 컴포넌트 클릭 → Logs 탭
2. **재사용 가능한 플로우**: 저장 → Templates으로 등록
3. **스케줄링**: Langflow의 Schedule 기능으로 자동 실행
4. **알림 설정**: Discord/Slack 웹훅 연동
5. **백테스팅**: 과거 데이터로 전략 검증

---

## 🆘 도움이 필요하면

- Langflow Docs: https://docs.langflow.org
- Trading 컴포넌트 README: `/home/user/langflow/src/lfx/src/lfx/components/trading/README.md`
- GitHub Issues: 버그 리포트

**Happy Trading! 🚀📈**
