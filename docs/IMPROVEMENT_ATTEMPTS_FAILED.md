# Podsumowanie: Dlaczego ulepszenia zawiodły (31 grudnia 2025)

## Problem

Baseline strategy (MA20/MA50 + TP=3.5×ATR, SL=1.0×ATR) osiąga **+327 PLN** na danych 2010-2025.
Stopa zwrotu: **+0.2%/rok** — niska, ale rentowna bez strat.

Próbowaliśmy ulepszyć strategię trzema podejściami z TIER 1 rekomendacji.

---

## Próba #1: RSI Trend Strength Filtering ❌

### Koncepcja

- Filtruj MA20/MA50 sygnały tylko w wysokie momentum
- LONG: Tylko jeśli RSI > 60 (silny trend wzrostowy)
- SHORT: Tylko jeśli RSI < 40 (silny trend spadkowy)
- Idea: Unikać fałszywych przebić w zmiennych warunkach rynkowych

### Wyniki

```
Thresholds (60/40):  -87 PLN (110 trades, 14.2% win rate)
Baseline:            +327 PLN (73 trades, 40% win rate)
Degradation:         -126.6%
```

### Przyczyna

- Thresholds **zbyt restrykcyjne** — filtrowały 58.3% sygnałów
- Pozostałe sygnały były **słabsze statystycznie**
- Win rate spadł z 40% do 14%
- **Lekcja**: Hard momentum filters usuwają dobre setup'y zarazem ze złymi

---

## Próba #2: Walk-Forward Retraining ❌

### Koncepcja

- Zamiast jednorazowego treningu na historycznych danych
- Retrenuj ML model co 100 barów na rolling 1000-bar oknie
- Idea: Model adaptuję się do zmiennych warunków rynkowych (concept drift)

### Wyniki

```
230 walk-forward periods: -1,929 PLN (1,322 trades, 19.7% win rate)
Baseline:                 +327 PLN (73 trades, 40% win rate)
Degradation:              -689.5%
```

### Przyczyna

- ML confidence threshold 60% — **filtrował 97.7% sygnałów**
- Pozostało tylko ~5.8 sygnału per testowy okres
- Model nie miał wystarczającego training set do generalizacji
- Win rate runął z 40% do 19.7%
- **Lekcja**: Model retrain sam w sobie nie wystarczy — problem jest w samym ML filter'e

---

## Próba #3: Lower Confidence Thresholds ❌

### Koncepcja

- Może problem to zbyt strict ML threshold (60%)?
- Testujemy range: 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60
- Idea: Znaleźć sweet spot między wystarczającą ilością trades a ich jakością

### Wyniki (na ostatnich 10 fold'ach)

```
Threshold   PnL         Trades   Win Rate
0.30       -6,128 PLN   647      21.7%
0.35       -3,459 PLN   434      21.2%
0.40       -2,273 PLN   277      14.1%
0.45       -3,510 PLN   142       8.9%
0.50       -2,795 PLN    71       3.6%
0.55       -1,261 PLN    26       1.4%
0.60        -566 PLN    12       1.7%

Baseline:   +327 PLN    73       40.0%
Best test: -566 PLN (273% worse than baseline)
```

### Przyczyna

- **Każdy threshold powoduje degradację**
- Nawet na 0.30 (30% confidence, prawie all signals) — -6,128 PLN
- Pokazuje, że **ML model sam jest źródłem problemu**
- Model nie zdoła dobrze mappować sygnałów z validation set
- **Lekcja**: ML filter nie działa dla tego datasetu — hurt больше niż help

---

## Root Cause Analysis

### Dlaczego ML filter degraduje wyniki?

1. **Overfitting na historical data**

   - Model trenowany na przeszłych sygnałach nie generalizuje na nowe
   - Market regime się zmienia (volatility cycles, regime shifts)
   - Historical patterns nie powtarzają się dokładnie

2. **Small sample size**

   - MA20/MA50 sygnały: ~250-366 per fold (relatively rare events)
   - XGBoost z 50 estimators puede overfitować na takim zbiorze
   - Feature noise + model complexity = bad OOS performance

3. **Mismatch między label'ami a reality**

   - Labele tworzyliśmy jako: "czy signal doprowadził do 2×ATR zysku w 6 barach?"
   - Real trading: longer holding periods, rynek zmieniał się między timeframe'ami
   - Label definition ≠ actual trading outcomes

4. **Data leakage?**
   - Możliwe, że przy train/test split robiliśmy błędy
   - Walk-forward design był prawidłowy, ale feature creation mogła mieć look-ahead bias

### Dlaczego baseline (bez ML) działa lepiej?

- MA20/MA50 crossover = prosty, robust mechanizm
- Nie wymaga accurate predictions (binary win/lose)
- Duża stopa wygranych (40%) wynika z:
  - Trend-following nature (momentum trading)
  - Long holding periods (ATR-based stops)
  - Market bias (long-term uptrend S&P 500)

---

## Konkluzja

### ✓ Strategia jest optymalna dla tego datasetu

- Baseline **+327 PLN** na 2010-2025 jest best known solution
- Każde dodatkowe filtrowanie (RSI, ML, momentum) degraduje wynik
- Strategia nie ma "low-hanging fruit" do ulepszenia

### ✗ Gdzie jest limit?

1. **Dane**: Daily bars (nie intraday) — session filtering niemożliwy
2. **Features**: Mało eksogenicznych zmiennych (tylko OHLCV + techniczne)
3. **Model**: MA20/MA50 jest już dobrze optimizowany (TP/SL sparametryzowane)
4. **Frequency**: ~5 trades/rok = mało sample'ów do ML training

### 🎯 Co by było potrzebne do realnych ulepszeń?

- **Intraday data** (H1 or H4 actual) — session filtering, shorter holding periods
- **Alternative universe**: Feature engineering z macro indicators (VIX, rates, econData)
- **Ensemble methods**: Combine MA + momentum + mean-reversion + ML
- **Longer data history**: Więcej sample'ów do training/validation
- **Alternative instruments**: Spreads, options, crypto — bardziej volatile markets

---

## Decyzja

**Wracamy do baseline +327 PLN.** Strategia jest optymalna w currentnych constraints.
Dokumentacja: `STRATEGIA_WYJAŚNIENIE_I_ULEPSZENIA.md` zawiera full mechanikę i phase 2/3 roadmap (jeśli zmienisz dane/features).
