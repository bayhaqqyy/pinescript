# Requirements Document

## Introduction

The XAU Quantum Signal Pipeline adds a Gold (XAUUSD) trading signal capability to the existing TradingView-to-Telegram alert system. It consists of a Pine Script v6 indicator that detects trading setups on XAUUSD using EMA Crossover + MACD confirmation, calculates dynamic Entry/TP/SL levels using ATR, and sends structured key-value alerts. The webhook (FastAPI) receives these alerts, parses the structured text format, and formats them into visually rich Telegram messages with action-based color logic.

## Glossary

- **Pine_Script_Indicator**: A TradingView Pine Script v6 indicator that monitors XAUUSD for trading setups and fires alerts with structured key-value data.
- **Webhook_Parser**: The FastAPI application (`main.py`) that receives TradingView alert payloads via HTTP POST and routes them to the appropriate formatter.
- **Alert_Formatter**: The Python function `format_custom_gold_alert()` that transforms raw XAU alert text into a visually rich HTML-formatted Telegram message.
- **Alert_Payload**: The structured plain-text message sent by the Pine Script indicator containing signal metadata in key-value format.
- **EMA_Crossover**: A technical analysis condition where a fast Exponential Moving Average crosses above or below a slow Exponential Moving Average.
- **MACD_Confirmation**: A secondary filter using the Moving Average Convergence Divergence histogram to confirm signal direction.
- **ATR**: Average True Range, a volatility indicator used to dynamically calculate price targets and stop-loss levels.
- **Telegram_Message**: The final HTML-formatted message delivered to the Telegram chat with visual styling based on signal direction.

## Requirements

### Requirement 1: Pine Script Signal Detection

**User Story:** As a gold trader, I want the Pine Script indicator to detect EMA Crossover setups confirmed by MACD on XAUUSD, so that I receive high-probability trade signals.

#### Acceptance Criteria

1. WHEN the fast EMA crosses above the slow EMA AND the MACD histogram value is greater than 0, THE Pine_Script_Indicator SHALL generate a BUY signal.
2. WHEN the fast EMA crosses below the slow EMA AND the MACD histogram value is less than 0, THE Pine_Script_Indicator SHALL generate a SELL signal.
3. THE Pine_Script_Indicator SHALL use configurable EMA lengths with default values of 9 (fast) and 21 (slow), accepting integer values between 2 and 200 where the fast EMA length must be less than the slow EMA length.
4. THE Pine_Script_Indicator SHALL use standard MACD parameters (12, 26, 9) for confirmation.
5. THE Pine_Script_Indicator SHALL evaluate signals only on confirmed bar close (barstate.isconfirmed).
6. IF the MACD histogram value is equal to 0 at the time of an EMA crossover, THEN THE Pine_Script_Indicator SHALL not generate a signal.

### Requirement 2: Dynamic Price Level Calculation

**User Story:** As a gold trader, I want Entry, Take Profit, and Stop Loss levels calculated dynamically using ATR, so that my trade levels adapt to current market volatility.

#### Acceptance Criteria

1. WHEN a BUY signal is generated, THE Pine_Script_Indicator SHALL set Entry to the current close price.
2. WHEN a BUY signal is generated, THE Pine_Script_Indicator SHALL set TP1 to Entry plus 1.0x ATR, and set TP2 to Entry plus 2.0x ATR, where ATR is calculated using the configured ATR period.
3. WHEN a BUY signal is generated, THE Pine_Script_Indicator SHALL set SL to Entry minus 1.5x ATR, where ATR is calculated using the configured ATR period.
4. WHEN a SELL signal is generated, THE Pine_Script_Indicator SHALL set Entry to the current close price.
5. WHEN a SELL signal is generated, THE Pine_Script_Indicator SHALL set TP1 to Entry minus 1.0x ATR, and set TP2 to Entry minus 2.0x ATR, where ATR is calculated using the configured ATR period.
6. WHEN a SELL signal is generated, THE Pine_Script_Indicator SHALL set SL to Entry plus 1.5x ATR, where ATR is calculated using the configured ATR period.
7. THE Pine_Script_Indicator SHALL use a configurable ATR period with a default value of 14 and a valid range of 1 to 200.
8. THE Pine_Script_Indicator SHALL use configurable ATR multipliers with default values of 1.0x (TP1), 2.0x (TP2), and 1.5x (SL), each accepting a valid range of 0.1 to 10.0.
9. IF the number of available bars is less than the configured ATR period, THEN THE Pine_Script_Indicator SHALL suppress signal generation until sufficient bars are available for ATR calculation.

### Requirement 3: Alert Payload Structure

**User Story:** As a system integrator, I want the Pine Script alert to send a structured key-value text payload, so that the webhook can reliably parse signal data.

#### Acceptance Criteria

1. WHEN a signal is generated, THE Pine_Script_Indicator SHALL send an alert containing the header line "👑 XAU QUANTUM SIGNAL" as the first line of the payload.
2. WHEN a signal is generated, THE Pine_Script_Indicator SHALL include the field "Ticker: XAUUSD" in the alert payload.
3. WHEN a signal is generated, THE Pine_Script_Indicator SHALL include the field "Action:" followed by BUY or SELL in the alert payload.
4. WHEN a signal is generated, THE Pine_Script_Indicator SHALL include the field "Entry:" followed by the entry price formatted to 2 decimal places.
5. WHEN a signal is generated, THE Pine_Script_Indicator SHALL include the field "TP1:" followed by the first take-profit price formatted to 2 decimal places.
6. WHEN a signal is generated, THE Pine_Script_Indicator SHALL include the field "TP2:" followed by the second take-profit price formatted to 2 decimal places.
7. WHEN a signal is generated, THE Pine_Script_Indicator SHALL include the field "SL:" followed by the stop-loss price formatted to 2 decimal places.
8. WHEN a signal is generated, THE Pine_Script_Indicator SHALL include the field "Context:" followed by a summary of the triggering conditions containing the signal direction, the EMA crossover description, and the MACD confirmation state, with a maximum length of 120 characters.
9. THE Pine_Script_Indicator SHALL fire alerts with frequency `alert.freq_once_per_bar_close` to prevent duplicate signals within the same bar.
10. THE Pine_Script_Indicator SHALL structure the alert payload as one field per line separated by newline characters, in the fixed order: header, Ticker, Action, Entry, TP1, TP2, SL, Context.

### Requirement 4: Webhook Alert Routing

**User Story:** As a system operator, I want the webhook to detect XAU Quantum Signal alerts and route them to the dedicated formatter, so that gold signals are displayed with their own visual style.

#### Acceptance Criteria

1. WHEN the webhook receives a plain-text body containing "XAU QUANTUM SIGNAL", THE Webhook_Parser SHALL route the payload to the `format_custom_gold_alert()` function and send the formatted result to Telegram.
2. WHEN the webhook receives a plain-text body that does not contain "XAU QUANTUM SIGNAL", THE Webhook_Parser SHALL continue processing with existing alert handlers without modification.
3. THE Webhook_Parser SHALL evaluate the "XAU QUANTUM SIGNAL" keyword check before the existing "US SWING HUNTER" and "US BANDAR AI" checks in the routing logic.
4. THE Webhook_Parser SHALL perform the "XAU QUANTUM SIGNAL" keyword match using case-sensitive comparison against the decoded request body.

### Requirement 5: Alert Formatter — Field Parsing

**User Story:** As a developer, I want the formatter to reliably extract all fields from the raw alert text, so that the Telegram message displays accurate trade data.

#### Acceptance Criteria

1. WHEN the Alert_Formatter receives a valid alert payload, THE Alert_Formatter SHALL extract the Ticker value by reading the text after the "Ticker:" prefix on that line, trimming leading and trailing whitespace, yielding a string of up to 20 characters.
2. WHEN the Alert_Formatter receives a valid alert payload, THE Alert_Formatter SHALL extract the Action value by reading the text after the "Action:" prefix on that line, trimming leading and trailing whitespace.
3. WHEN the Alert_Formatter receives a valid alert payload, THE Alert_Formatter SHALL extract the Entry price by reading the text after the "Entry:" prefix on that line, trimming whitespace, and interpreting the result as a numeric value formatted to 2 decimal places.
4. WHEN the Alert_Formatter receives a valid alert payload, THE Alert_Formatter SHALL extract the TP1 price by reading the text after the "TP1:" prefix on that line, trimming whitespace, and interpreting the result as a numeric value formatted to 2 decimal places.
5. WHEN the Alert_Formatter receives a valid alert payload, THE Alert_Formatter SHALL extract the TP2 price by reading the text after the "TP2:" prefix on that line, trimming whitespace, and interpreting the result as a numeric value formatted to 2 decimal places.
6. WHEN the Alert_Formatter receives a valid alert payload, THE Alert_Formatter SHALL extract the SL price by reading the text after the "SL:" prefix on that line, trimming whitespace, and interpreting the result as a numeric value formatted to 2 decimal places.
7. WHEN the Alert_Formatter receives a valid alert payload, THE Alert_Formatter SHALL extract the Context description by reading the text after the "Context:" prefix on that line, trimming leading and trailing whitespace, yielding a string of up to 200 characters.
8. IF a required field line is missing from the alert payload or the value after the colon is empty, THEN THE Alert_Formatter SHALL use a default placeholder value ("???" for text fields Ticker, Action, and Context; "0.00" for price fields Entry, TP1, TP2, and SL).
9. IF a price field (Entry, TP1, TP2, or SL) contains a value that cannot be interpreted as a numeric value, THEN THE Alert_Formatter SHALL treat that field as missing and apply the default placeholder "0.00".
10. IF the Action value is not "BUY" and not "SELL", THEN THE Alert_Formatter SHALL treat the Action as "???" for display purposes and default to neutral formatting.

### Requirement 6: Telegram Message Formatting

**User Story:** As a Telegram channel subscriber, I want gold signals displayed with rich visual formatting and action-based colors, so that I can quickly identify signal direction and key levels.

#### Acceptance Criteria

1. WHEN the Action is "BUY", THE Alert_Formatter SHALL use the 🟢 emoji in the message header line alongside the signal title.
2. WHEN the Action is "SELL", THE Alert_Formatter SHALL use the 🔴 emoji in the message header line alongside the signal title.
3. THE Alert_Formatter SHALL format the Telegram message using HTML parse mode with bold tags (`<b>`) for field labels including Entry, TP1, TP2, SL, and Context.
4. THE Alert_Formatter SHALL include Entry, TP1, TP2, and SL prices formatted to 2 decimal places in the formatted message body.
5. THE Alert_Formatter SHALL include a Risk:Reward ratio displayed to 1 decimal place, calculated as (TP1 - Entry) / (Entry - SL) for BUY signals and (Entry - TP1) / (SL - Entry) for SELL signals.
6. IF the Risk:Reward ratio denominator is zero, THEN THE Alert_Formatter SHALL display the Risk:Reward value as "N/A".
7. THE Alert_Formatter SHALL include the Context field value in the formatted message.
8. THE Alert_Formatter SHALL include a hashtag section with #XAU_QUANTUM and #XAUUSD at the end of the message.
9. THE Alert_Formatter SHALL structure the message in the following section order: header with emoji and title, separator line, price levels, separator line, context and Risk:Reward, separator line, hashtags.
10. THE Alert_Formatter SHALL use separator lines (━━━━━━━━━━━━━━━━━━) to visually divide message sections.

### Requirement 7: Health Endpoint Update

**User Story:** As a system operator, I want the health endpoint to reflect the new XAU Quantum Signal capability, so that I can verify the pipeline is configured.

#### Acceptance Criteria

1. THE Webhook_Parser SHALL include "XAU Quantum Signal (plain text)" in the `supported_alerts` list returned by the `/health` endpoint.
2. THE Webhook_Parser SHALL continue to include all previously existing entries in the `supported_alerts` list ("US Swing Hunter v2 (plain text)", "US Bandar AI v2 (plain text)", "IDX Bandar AI (JSON legacy)", "IDX Scalping (JSON legacy)") when returning the `/health` endpoint response.
3. THE Webhook_Parser SHALL return the `/health` endpoint response as a JSON object containing the fields `status`, `telegram_configured`, and `supported_alerts`.
