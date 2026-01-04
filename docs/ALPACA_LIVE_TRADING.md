# Alpaca Paper Trading Setup

## 1) Utwórz konto Paper

- https://app.alpaca.markets/signup
- W dashboardzie wygeneruj `API Key ID` i `Secret Key`
- Tryb PAPER (bezpieczny sandbox)

## 2) Konfiguracja kluczy

**Nie commituj kluczy!**

- Zapisz w `config/alpaca_config.json` (gitignored) **albo** w zmiennych środowiskowych:
  - `ALPACA_API_KEY`
  - `ALPACA_SECRET_KEY`
  - `ALPACA_BASE_URL` (domyślnie `https://paper-api.alpaca.markets`)

Przykład `config/alpaca_config.json`:

```json
{
  "alpaca": {
    "api_key": "YOUR_ALPACA_API_KEY_ID",
    "secret_key": "YOUR_ALPACA_SECRET_KEY",
    "base_url": "https://paper-api.alpaca.markets"
  }
}
```

## 3) Instalacja klienta

```bash
pip install -r requirements.txt
```

## 4) Smoke test API

```bash
python src/live/alpaca_connector.py
```

Oczekiwane logi: status konta, equity, zegar rynku, ostatni quote SPY.

## 5) Minimalny przykład (inline)

```python
import alpaca_trade_api as tradeapi

API_KEY = "YOUR_KEY"
SECRET_KEY = "YOUR_SECRET"
BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')
account = api.get_account()
print(account.status, account.equity)
```

## 6) Kolejne kroki

- Dodać warstwę strategii (sygnały) i wywoływać `submit_order`
- Zaimplementować risk mgmt: size = risk_per_trade / stop_distance
- Zapisać logi (CSV/DB) i monitorować w Streamlit

---

**Uwaga:** Handel algorytmiczny wiąże się z ryzykiem. Paper trading jest bezpieczny; przed live upewnij się, że strategia jest przetestowana.
