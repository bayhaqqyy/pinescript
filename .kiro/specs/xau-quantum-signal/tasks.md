# Implementation Plan: XAU Quantum Signal

## Overview

Implement the XAU Quantum Signal pipeline end-to-end: a Pine Script v6 indicator for XAUUSD signal detection with ATR-based price levels, a Python formatter function for Telegram message formatting, webhook routing updates, and health endpoint changes. The implementation follows the existing architectural patterns (US Swing Hunter, US Bandar AI) for consistency.

## Tasks

- [x] 1. Create Pine Script v6 indicator
  - [x] 1.1 Create `tv_scripts/xau_quantum_signal.pine` with indicator declaration and configurable inputs
    - Declare Pine Script v6 indicator with `indicator()` call
    - Add input parameters: `emaFastLen` (default 9, range 2–200), `emaSlowLen` (default 21, range 2–200), `macdFast` (12), `macdSlow` (26), `macdSignal` (9), `atrPeriod` (default 14, range 1–200), `atrMultTP1` (default 1.0, range 0.1–10.0), `atrMultTP2` (default 2.0, range 0.1–10.0), `atrMultSL` (default 1.5, range 0.1–10.0)
    - Ensure `emaFastLen` < `emaSlowLen` via input constraints
    - _Requirements: 1.3, 1.4, 2.7, 2.8_

  - [x] 1.2 Implement signal detection logic (EMA crossover + MACD confirmation)
    - Calculate fast and slow EMA using `ta.ema()`
    - Detect crossover with `ta.crossover()` and crossunder with `ta.crossunder()`
    - Calculate MACD histogram using `ta.macd()`
    - Generate BUY signal when EMA crosses above AND MACD histogram > 0
    - Generate SELL signal when EMA crosses below AND MACD histogram < 0
    - Suppress signal when MACD histogram == 0
    - Only evaluate on `barstate.isconfirmed`
    - _Requirements: 1.1, 1.2, 1.5, 1.6_

  - [x] 1.3 Implement ATR-based dynamic price level calculation
    - Calculate ATR using `ta.atr(atrPeriod)`
    - Guard: suppress signal if `bar_index < atrPeriod` (insufficient bars)
    - BUY: Entry = close, TP1 = Entry + atrMultTP1 * ATR, TP2 = Entry + atrMultTP2 * ATR, SL = Entry - atrMultSL * ATR
    - SELL: Entry = close, TP1 = Entry - atrMultTP1 * ATR, TP2 = Entry - atrMultTP2 * ATR, SL = Entry + atrMultSL * ATR
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.9_

  - [x] 1.4 Implement structured alert payload and fire alert
    - Build alert message string with header "👑 XAU QUANTUM SIGNAL", Ticker, Action, Entry, TP1, TP2, SL, Context fields (one per line, newline-separated)
    - Format prices to 2 decimal places using `str.tostring(value, "#.##")`
    - Build Context string with signal direction, EMA crossover description, MACD state (max 120 chars)
    - Fire alert with `alert()` using `alert.freq_once_per_bar_close`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [x] 2. Implement Python alert formatter
  - [x] 2.1 Create `format_custom_gold_alert()` function in `main.py` with field parsing logic
    - Add function signature: `def format_custom_gold_alert(raw: str) -> str`
    - Split payload on newlines, iterate lines
    - Extract Ticker, Action, Entry, TP1, TP2, SL, Context by matching prefixes and splitting on ":"
    - Strip whitespace from extracted values
    - Cap Ticker at 20 chars, Context at 200 chars
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 2.2 Implement default/fallback handling for missing or invalid fields
    - Use "???" for missing/empty text fields (Ticker, Action, Context)
    - Use "0.00" for missing/non-numeric price fields (Entry, TP1, TP2, SL)
    - Validate Action is exactly "BUY" or "SELL"; otherwise treat as "???"
    - Wrap price parsing in try/except for float conversion failures
    - _Requirements: 5.8, 5.9, 5.10_

  - [x] 2.3 Implement Risk:Reward calculation and Telegram message formatting
    - Calculate R:R: BUY = (TP1 - Entry) / (Entry - SL), SELL = (Entry - TP1) / (SL - Entry)
    - If denominator == 0, display "N/A"; otherwise format to 1 decimal place
    - Build HTML message with: header line (🟢 for BUY, 🔴 for SELL), separator lines (━━━━━━━━━━━━━━━━━━), price levels with bold labels, Context + R:R section, hashtags (#XAU_QUANTUM #XAUUSD)
    - Use `<b>` tags for field labels
    - Format all prices to 2 decimal places
    - Sections in order: header, separator, price levels, separator, context+R:R, separator, hashtags
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10_

  - [ ]* 2.4 Write property test for parsing round-trip (Property 1)
    - **Property 1: Parsing round-trip preserves field values**
    - Generate random valid payloads with random prices (1000–5000), random tickers, BUY/SELL actions
    - Verify all field values appear in the formatted output (prices to 2dp, text as-is)
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**

  - [ ]* 2.5 Write property test for graceful degradation (Property 2)
    - **Property 2: Graceful degradation for malformed payloads**
    - Generate payloads with random subsets of fields missing or garbage in price positions
    - Verify output is non-empty valid string with default placeholders, no exceptions raised
    - **Validates: Requirements 5.8, 5.9, 5.10**

  - [ ]* 2.6 Write property test for action emoji (Property 3)
    - **Property 3: Action determines directional emoji**
    - Generate valid payloads with BUY or SELL action
    - Verify BUY → 🟢 present and 🔴 absent in header; SELL → 🔴 present and 🟢 absent in header
    - **Validates: Requirements 6.1, 6.2**

  - [ ]* 2.7 Write property test for Risk:Reward calculation (Property 4)
    - **Property 4: Risk:Reward calculation correctness**
    - Generate random Entry/TP1/SL triples with non-zero denominator
    - Compute expected R:R, verify output matches to 1 decimal place
    - Test zero-denominator case displays "N/A"
    - **Validates: Requirements 6.5, 6.6**

  - [ ]* 2.8 Write property test for message structural integrity (Property 5)
    - **Property 5: Message structural integrity**
    - Generate random valid payloads
    - Verify output contains: `<b>` tags for labels, prices to 2dp, Context value, separator lines, hashtags #XAU_QUANTUM and #XAUUSD, sections in correct order
    - **Validates: Requirements 6.3, 6.4, 6.7, 6.8, 6.9, 6.10**

- [x] 3. Checkpoint - Ensure formatter works correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Update webhook routing and health endpoint
  - [x] 4.1 Add "XAU QUANTUM SIGNAL" routing in `handle_webhook` function in `main.py`
    - Insert `if "XAU QUANTUM SIGNAL" in body_str:` check BEFORE the existing "HEARTBEAT TEST" check in the plain-text routing block
    - Route matched payloads to `format_custom_gold_alert(body_str)`
    - Case-sensitive match using Python `in` operator
    - Existing handlers remain unchanged
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 4.2 Update `/health` endpoint to include XAU Quantum Signal in supported_alerts
    - Add "XAU Quantum Signal (plain text)" to the `supported_alerts` list
    - Preserve all existing entries in the list
    - Ensure response still returns `status`, `telegram_configured`, and `supported_alerts` fields
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 4.3 Write unit tests for webhook routing and health endpoint
    - Test "XAU QUANTUM SIGNAL" in body routes to `format_custom_gold_alert()`
    - Test routing priority: XAU check fires before "US SWING HUNTER" check
    - Test case sensitivity: lowercase "xau quantum signal" does NOT trigger handler
    - Test health endpoint returns new entry plus all existing entries
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 7.1, 7.2, 7.3_

- [x] 5. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Pine Script (tasks 1.x) runs in TradingView and cannot be unit-tested in Python — manual verification on chart required
- Python formatter and routing (tasks 2.x, 4.x) are fully testable with pytest + hypothesis

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "2.2"] },
    { "id": 2, "tasks": ["1.3", "2.3"] },
    { "id": 3, "tasks": ["1.4", "2.4", "2.5", "2.6", "2.7", "2.8"] },
    { "id": 4, "tasks": ["4.1", "4.2"] },
    { "id": 5, "tasks": ["4.3"] }
  ]
}
```
