# AUDIT REPOZYTORIA - Niepotrzebne Pliki do Usunięcia

## Klasyfikacja Plików w `src/models/`

### ✅ POTRZEBNE (Core)
- `final_validation.py` - Główny validation script (12.5 KB)
- `run_oos_sweep.py` - OOS sweep automation (6.3 KB)
- `run_sensitivity_direct.py` - Subperiod sensitivity (8.9 KB)
- `hybrid_ma_ml_filter.py` - Baseline strategy (9.1 KB)

### ❌ NIEPOTRZEBNE (Eksperymentalne, Obsolete)
Pliki poniżej były używane do eksperymentów w przeszłości. Mogą być usunięte:

**1. Stare Baseline'y (6 plików)**
- `hybrid_ma_ml_simple.py` - Uproszczona wersja (7.0 KB)
- `reversed_hybrid.py` - Stara iteracja (7.4 KB)
- `rule_based_ma_baseline.py` - Rule-based variant (4.9 KB)
- `simple_15pct_risk.py` - Eksperyment (9.2 KB)
- `test_1pct_risk.py` - Eksperyment (6.8 KB)
- `final_optimized.py` - Stara optymalizacja (12.2 KB)

**2. Eksperymenty RSI/Mean Reversion (4 pliki)**
- `daily_rsi_meanreversion.py` - MR eksperyment (5.8 KB)
- `rsi_slope_experiments.py` - RSI slope test (3.2 KB)
- `grid_search_rsi_ema.py` - Grid search (3.9 KB)
- `boost_profits.py` - Eksperyment (12.7 KB)

**3. Stare Optimization Scripts (6 plików)**
- `optimize_reversed_hybrid.py` - Stara optymalizacja (8.5 KB)
- `optimize_tp_sl_manual.py` - Manual tuning (8.7 KB)
- `conservative_risk_sweep.py` - Risk sweep (3.8 KB)
- `expanded_risk_sweep.py` - Risk sweep (2.8 KB)
- `walk_forward.py` - Stary WF (3.2 KB)
- `walk_forward_conservative.py` - Stary WF (6.4 KB)

**4. Utility Scripts (3 pliki)**
- `predict.py` - Prediction (1.8 KB)
- `feature_analysis.py` - Feature analysis (2.7 KB)
- `feature_selection_runner.py` - Feature selection (2.0 KB)

**5. Plotting/Analysis (3 pliki)**
- `plot_top_combos.py` - Plotting (2.4 KB)
- `plot_top_combos_compare.py` - Plotting (0.9 KB)
- `run_quick_grid.py` - Quick grid (0.3 KB)

**6. Pozostałe Training Scripts (2 pliki)**
- `train_xgb.py` - Training (4.8 KB)
- `walk_forward_regime_aware.py` - Regime WF (8.6 KB)
- `calculate_sharpe_sortino.py` - Metrics (3.6 KB)
- `run_subperiod_sensitivity.py` - Stara wersja (8.7 KB) - zamiast `run_sensitivity_direct.py`

## Podsumowanie

| Status | Pliki | Razem KB | Akcja |
|--------|-------|----------|-------|
| ✅ Core | 4 | ~37 | Zachowaj |
| ❌ Eksperymentalne | 28 | ~176 | Usuń |

**Całkowite oszczędności**: ~176 KB (mało, ale czystość kodu)

## Plik Manifest - Jaki Plik Co Robi?

### CORE PRODUCTION SCRIPTS

**1. final_validation.py**
```
Wejście:  CSV ze strategią i sygnałami
Wyjście:  JSON z metrykami (P&L, win rate, DD)
Parametry: TP_MULT, SL_MULT, CONF_PERCENTILE (env vars)
Użycie:   Validate dowolną kombinację parametrów
```

**2. run_oos_sweep.py**
```
Wejście:  Pełny dataset
Wyjście:  CSV z wynikami 4 OOS windows × 3 percentiles
Użycie:   Sprawdzić out-of-sample performance
```

**3. run_sensitivity_direct.py**
```
Wejście:  Pełny dataset
Wyjście:  CSV z 7 subperiodów × 25 TP/SL combos
Użycie:   Analiza wrażliwości parametrów
```

**4. hybrid_ma_ml_filter.py**
```
Wejście:  CSV + parametry
Wyjście:  Sygnały, trades, metryki
Użycie:   Symulacja strategii z różnymi parametrami
```

---

## REKOMENDACJE

### Opcja 1: CONSERVATIVE (Zachowaj Wszystko)
- Przydatne dla audytu historii
- Może być przydatne do porównań

### Opcja 2: AGGRESSIVE (Usuń Wszystko Poza Core)
```bash
# Usuń w powłoce:
rm src/models/hybrid_ma_ml_simple.py
rm src/models/reversed_hybrid.py
rm src/models/rule_based_ma_baseline.py
rm src/models/simple_15pct_risk.py
# ... itd (28 plików)
```
- Czystsze repo
- Łatwiej się orientować w kodzie
- Można zawsze przywrócić z Git

### Opcja 3: BALANCED (Usuń Tylko Duplikaty)
Zachowaj:
- `final_validation.py`, `run_oos_sweep.py`, `run_sensitivity_direct.py`
- `hybrid_ma_ml_filter.py`
- `train_xgb.py` (jeśli planujesz modyfikować model)

Usuń:
- Wszystkie `hybrid_ma_ml_simple.py`, `reversed_hybrid.py` (duplikaty)
- Wszystkie `walk_forward*.py` poza najnowszym
- Wszystkie `optimize*.py` (już optymalizowane)
- Wszystkie `run_quick_grid.py`, `run_subperiod_sensitivity.py` (stare wersje)

---

## ROOT DIRECTORY CLEANUP

### Niepotrzebne Pliki Główne
```
❌ test_sensitivity.py - Test script (można usunąć)
❌ analiza_2008_do_dziś.py - Analysis (można usunąć)
✅ oblicz_zwroty.py - Zwroty analysis (przydatny)
✅ visualize_sensitivity.py - Visualization (przydatny)
✅ analyze_sensitivity.py - Analysis (przydatny)
```

### Dokumentacja
```
✅ PODSUMOWANIE_WRAŻLIWOŚĆ.md - Polski summary
✅ STRATEGIA_WYJAŚNIENIE_I_ULEPSZENIA.md - Nowy plik
✅ EXECUTION_GUIDE.md - Deployment guide
✅ FINAL_SUMMARY.md - OOS summary
✅ README.md - Overview
```

---

## STRUKTURA PO CLEANUP

```
sp500_agent/
├── src/
│   ├── models/
│   │   ├── final_validation.py          ✅
│   │   ├── run_oos_sweep.py             ✅
│   │   ├── run_sensitivity_direct.py    ✅
│   │   ├── hybrid_ma_ml_filter.py       ✅
│   │   └── train_xgb.py                 ✅
│   ├── backtest/
│   └── ...
├── experiments/
│   ├── exp_015_final_validation/
│   ├── exp_025_oos_sweep/
│   └── exp_026_subperiod_sensitivity/
├── data/
│   └── processed/sp500_features_H4.csv
├── STRATEGIA_WYJAŚNIENIE_I_ULEPSZENIA.md    ✅ NEW
├── PODSUMOWANIE_WRAŻLIWOŚĆ.md               ✅
├── EXECUTION_GUIDE.md                       ✅
├── FINAL_SUMMARY.md                         ✅
├── README.md                                ✅
└── oblicz_zwroty.py                         ✅ (main analysis)
```

---

## DECYZJA

**Rekomendacja: OPCJA 3 (BALANCED)**

Usuń duplikaty i stare eksperymenty, zachowaj core production + nowe dokumenty.

**Szacunkowy wynik:**
- Przed: ~30 plików w models/, ~40 głównie
- Po: ~5 plików w models/, ~15 głównie
- Oszczędności: ~176 KB
- Przejrzystość: +200% (łatwiej znaleźć to co potrzeba)

