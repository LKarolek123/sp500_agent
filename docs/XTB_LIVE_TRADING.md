# XTB Live Trading Setup

## Quick Start

### 1. Załóż konto demo XTB

```
https://www.xtb.com/pl/demo
```

Dostaniesz:

- Login (numer konta)
- Hasło
- Dostęp do xStation i API

### 2. Edytuj config

```bash
nano config/xtb_config.json
```

Wpisz swoje credentials:

```json
{
  "xtb_demo": {
    "user_id": "123456789",
    "password": "twoje_haslo",
    "mode": "demo"
  }
}
```

### 3. Test połączenia

```bash
# Uruchom test connector
python src/live/xtb_connector.py

# Jeśli działa, zobaczysz:
# ✓ Connected successfully
# 📊 Account Info: balance, equity, etc.
```

### 4. Uruchom bota

```bash
python src/live/live_trader.py \
  --user 123456789 \
  --password twoje_haslo \
  --mode demo \
  --symbol US500 \
  --check-interval 60
```

Bot będzie:

- Sprawdzać sygnały co 60 sekund
- Otwierać zlecenia przy MA crossover
- Ustawiać SL/TP automatycznie
- Logować wszystko do konsoli

### 5. Zatrzymanie

```
Ctrl+C - zatrzymuje bota i zamyka otwarte pozycje
```

---

## Architektura

```
src/live/
├── __init__.py
├── xtb_connector.py     # Niskopoziomowe API (WebSocket/TCP)
└── live_trader.py       # Wysokopoziomowa logika trading

config/
└── xtb_config.json      # Credentials (gitignored!)
```

---

## XTB API - Najważniejsze komendy

### Połączenie

```python
from src.live.xtb_connector import XTBConnector

with XTBConnector(user, password, mode="demo") as xtb:
    # ... trading logic
```

### Account info

```python
info = xtb.get_account_info()
# {'balance': 10000.0, 'equity': 10023.45, ...}
```

### Aktualna cena

```python
price = xtb.get_current_price("US500")
# 4500.50
```

### Otwórz pozycję

```python
order_id = xtb.open_trade(
    symbol="US500",
    cmd_type=0,  # 0=BUY, 1=SELL
    volume=0.1,  # 0.1 lot
    sl=4450.0,   # Stop loss
    tp=4550.0    # Take profit
)
```

### Zamknij pozycję

```python
xtb.close_trade(order_id, volume=0.1)
```

### Lista otwartych

```python
trades = xtb.get_open_trades()
for t in trades:
    print(f"Order #{t['order']}: {t['symbol']} {t['profit']}")
```

---

## Live Trader - Parametry

```python
trader = LiveTrader(
    xtb=xtb,
    symbol="US500",        # S&P 500
    fast_ma=10,            # EMA10
    slow_ma=100,           # EMA100
    tp_atr_mult=5.0,       # TP = 5×ATR
    sl_atr_mult=1.75,      # SL = 1.75×ATR
    risk_per_trade=0.008,  # 0.8% kapitału na trade
    check_interval=60      # Sprawdzanie co 60s
)
```

### Strategia:

1. Zbiera ceny co `check_interval` sekund
2. Liczy EMA10/EMA100
3. Wykrywa crossover (fast > slow = LONG, fast < slow = SHORT)
4. Otwiera pozycję z ATR-based SL/TP
5. Monitoruje P&L
6. Zamyka gdy SL/TP hit lub nowy sygnał

---

## Parametry dla US500 (S&P 500)

### Volume (lots):

- `1.0 lot = $1 per point`
- Przykład: S&P @ 4500, move 10 punktów = $10 P&L na 1 lot
- Minimum: `0.01 lot`

### Spread:

- Demo: ~1-2 punkty
- Real: ~0.5-1 punkt

### Margin:

- Leverage 1:10 (może się różnić)
- Dla 1 lot @ 4500: margin ~$450

---

## Bezpieczeństwo

⚠️ **WAŻNE:**

1. **Zawsze testuj na DEMO** przed Real
2. **Nigdy nie commituj credentials** (gitignored)
3. **Ustawiaj risk_per_trade małe** (0.5-1%)
4. **Monitoruj equity** - bot nie ma hard stop loss na konto
5. **Testuj w godzinach sesji USA** (15:30-22:00 CET)

---

## Troubleshooting

### "Connection refused"

- Sprawdź login/hasło
- Sprawdź czy konto demo aktywne (ważne 30 dni)

### "Invalid symbol"

- US500 = S&P 500
- Inne: `DE30` (DAX), `UK100` (FTSE), `US30` (Dow)
- Lista: https://www.xtb.com/pl/oferta-handlowa

### "Insufficient margin"

- Zmniejsz `risk_per_trade`
- Zwiększ saldo demo (poproś support)

### Bot nie otwiera pozycji

- Sprawdź czy są crossovery (wolna strategia)
- Sprawdź logi: `print(signal)`
- Zmniejsz MA periods dla więcej sygnałów

---

## Monitoring

### Real-time logs:

```bash
python src/live/live_trader.py ... | tee logs/bot_$(date +%Y%m%d).log
```

### Equity tracking:

Bot loguje P&L przy każdym cyklu. Można dodać:

- Zapis do CSV
- Push do Telegram
- Dashboard Streamlit

---

## TODO (rozbudowa):

- [ ] Streamlit dashboard dla live monitoring
- [ ] Telegram alerts (otwarte/zamknięte pozycje)
- [ ] Backup/restore state (crash recovery)
- [ ] Multi-symbol trading
- [ ] Advanced filters (volume, time-of-day)
- [ ] Portfolio management (max exposure)

---

## API Documentation

Full docs: http://developers.xtb.com/documentation/

Key endpoints:

- `login` - Authentication
- `getMarginLevel` - Account info
- `getSymbol` - Symbol data
- `getTrades` - Open positions
- `tradeTransaction` - Open/close/modify

---

**Autor:** Karol  
**Licencja:** MIT  
**Ostrzeżenie:** Trading wiąże się z ryzykiem. Bot do celów edukacyjnych.
