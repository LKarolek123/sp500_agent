# Post LinkedIn - Wersja polska

---

## 🚀 Budowanie bota tradingowego napędzanego sztuczną inteligencją: Wyniki na żywo

W ostatnich tygodniach pracuję nad algorytmiczną strategią tradingową, która łączy analizę techniczną z optymalizacją uczenia maszynowego. Dziś chciałbym się podzielić postępem i wynikami z rzeczywistego handlu.

**Co zbudowaliśmy:**

✅ Strategia EMA 10/100 optymalizowana ML
✅ 5 wskaźników technicznych ocenianych przez uczenie maszynowe (optymalizacja Optuna)
• Siła momentum EMA (waga: 33.57%)
• Sygnały RSI wyprzedania/wykupienia (waga: 24.04%)
• Detekcja wsparcia i oporu (waga: 19.79%)
• Potwierdzenie trendu MACD (waga: 8.59%)
• Analiza wolumenu (waga: 4.01%)
✅ Dynamiczne wielkości pozycji i zarządzanie ryzykiem
✅ Framework backtestingu w czasie rzeczywistym
✅ Bot tradingowy na żywo na brokerze Alpaca

**Kluczowe metryki:**

📈 **Wyniki z handlu na żywo (13 grudnia 2025 - 10 stycznia 2026)**
• Wartość portfela: $104,904.93
• Kapitał początkowy: $100,000
• Zwrot: **+4.9% w ~4 tygodnie** ✨
• Średni dzienny zwrot: +0.70%
• Wskaźnik wygranych: 61.7% wszystkich transakcji
• Max drawdown: 0.44%
• Status: ✅ LIVE & RENTOWNY

🧪 **Validacja backtestu (900 dni danych historycznych)**

Strategia V2 (10 pozycji, wskaźniki ML):
• Zysk: +1.59% | Transakcje: 81 | Win rate: 61.7%

Strategia V1 (5 pozycji, baseline):
• Zysk: +0.65% | Transakcje: 78 | Win rate: 60.3%

🏆 **V2 przewyższa V1 o +146% (poprawa względna)**

Trading 8 głównych akcji S&P 500: TSLA, AMZN, META, GOOGL, JNJ, JPM, DIS, LLY
Wszystkie symbole wykazują rentowność w backtestach

**Podróż techniczna:**

1. **Zbieranie danych**: Pobrano 2+ lat danych historycznych OHLCV
2. **Inżynieria cech**: Zaimplementowano 5 wskaźników technicznych
3. **Optymalizacja ML**: Użyto frameworku Optuna do optymalizacji wag
   - Przeprowadzono 50 udanych prób z parametrami
   - Znaleziono optymalne wagi maksymalizujące Sharpe ratio
4. **A/B Testing**: Porównanie V1 vs V2 na różnych okresach (100/200/500/900 dni)
5. **Wdrożenie na żywo**: Bot produkcyjny na VPS Hetzner od grudnia

**Co sprawia, że to działa:**

🎯 **Multi-Signal Confirmation**: Wejście tylko gdy 5 wskaźników się zgadza (wynik ≥ 40)
→ Znacznie mniej fałszywych wybić

🎯 **Ryzyko na transakcję**: Limitowane do 1.5% kapitału konta
→ Zrównoważony wzrost nawet w serii przegranych

🎯 **Dywersyfikacja pozycji**: Do 10 otwartych transakcji jednocześnie
→ 87% lepsze zwroty niż limit do 5 pozycji

🎯 **Automatyczna dyscyplina**: Brak emocjonalnych decyzji, ścisła egzekucja TP/SL
→ Każda transakcja podlega tym samym zasadom

🎯 **Dynamiczne ważenie**: Rozmiar pozycji skaluje się z pewności wskaźnika
→ Większe pozycje przy wysokiej pewności

**Stack techniczny:**

Python 3.13 | Optuna (optymalizacja ML) | yfinance | Alpaca API | NumPy | Pandas

---

## W przyszłości

Strategia jest obecnie wdrożona w produkcji, generując konsekwentne dzienne zwroty przy konserwatywnym zarządzaniu ryzykiem. Dokumentuję tę podróż, aby pokazać jak podejście oparte na danych może poprawić wyniki tradingu.

**Zainteresowany(-a):**

- Strategiami algorytmicznego handlu?
- Pythonem do finansów ilościowych?
- Optymalizacją ML dla handlu?
- Monitoringiem i automatyzacją w czasie rzeczywistym?

Zapraszam do kontaktu! Chętnie dyskutuję o architekturze systemów tradingowych, metodach backtestingu czy najlepszych praktykach wdrażania.

---

**#AlgorithmicTrading #MachineLearning #Trading #Python #FinTech #Optuna #Backtesting #FinanseIlościowe #TradingBot #DataDriven**

---

_Zastrzeżenie: Wyniki przeszłości nie gwarantują przyszłych rezultatów. Trading niesie ryzyko straty. To projekt edukacyjny, a nie porada finansowa._
