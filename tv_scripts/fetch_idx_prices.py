"""
Fetch all IDX stock prices from Yahoo Finance and filter those below 1000 IDR.
Fetch all IDX stock prices from Yahoo Finance and filter those below 1000 IDR.
Output: idx_prices_v2.json with tier_eligible and avg_transaction_value_20
"""
import yfinance as yf
import json
import time
import os
from datetime import date

# Comprehensive list of IDX tickers (all known active tickers on BEI)
# Format for Yahoo Finance: TICKER.JK
idx_tickers = [
    # === BANKING & FINANCE ===
    "BBRI", "BMRI", "BBCA", "BBNI", "BBTN", "BRIS", "BBYB", "AGRO", "NISP", "PNBN",
    "BTPS", "BGTG", "MEGA", "BNGA", "BDMN", "BNLI", "BNII", "BJTM", "BJBR", "BSIM",
    "BMAS", "NOBU", "BABP", "BINA", "BANK", "BEKS", "MCOR", "SDRA", "DNAR", "ARTO",
    "BHAT", "AMAR", "BACA", "BCIC", "AGRS",
    
    # === MINING & ENERGY ===
    "ANTM", "TINS", "INCO", "MEDC", "ELSA", "HRUM", "DSSA", "MBMA", "MDKA", "FIRE",
    "ADRO", "ITMG", "PTBA", "BUMI", "BORN", "BYAN", "DEWA", "ENRG", "RAAM", "ARTI",
    "COAL", "ZINC", "GTBO", "BOSS", "GEMS", "BRMS", "PSAB", "INDY", "SMMT", "TOBA",
    "BSSR", "KKGI", "MYOH", "ARII", "SMRU", "APEX", "MITI", "KARW", "ESSA",
    
    # === INFRASTRUCTURE & CONSTRUCTION ===
    "ADHI", "WIKA", "PTPP", "WSKT", "WTON", "JSMR", "SMBR", "SMCB", "TBIG", "TOWR",
    "WSBP", "ACST", "NRCA", "TOTL", "DGIK", "JKON", "SSIA", "MTRA", "PBSA",
    
    # === PROPERTY & REAL ESTATE ===
    "BSDE", "CTRA", "SMRA", "PWON", "LPKR", "APLN", "ASRI", "DILD", "KIJA", "MDLN",
    "PPRO", "NIRO", "FORZ", "CLAY", "SAME", "TOPS", "DEAL", "BEBS", "PURA", "MTSM",
    "LPCK", "DUTI", "JRPT", "RDTX", "GWSA", "BKSL", "EMDE", "GPRA", "ELTY", "MTLA",
    "BCIP", "URBN", "MMLP",
    
    # === CONSUMER & RETAIL ===
    "INDF", "ICBP", "MYOR", "ROTI", "ACES", "LPPF", "MAPI", "ERAA", "SRIL", "TPIA",
    "BRPT", "UNVR", "GGRM", "HMSP", "KLBF", "KAEF", "SIDO", "DVLA", "TSPC", "PYFA",
    "ULTJ", "CPIN", "JPFA", "MAIN", "FOOD", "TRIO", "MDIA", "KIOS", "BOLA", "AGAR",
    "POLL", "SBAT", "GOOD", "AISA", "CLEO", "CAMP", "HOKI", "PANI", "KEJU", "IKAN",
    "CARS", "LCKM", "SMAR", "DSNG", "TBLA",
    
    # === TELCO & TECH ===
    "TLKM", "ISAT", "EXCL", "FREN", "GOTO", "BUKA", "WIFI", "EDGE", "KREN", "LUCK",
    "TELE", "INET", "DCII", "DIGI", "MSIN", "YELO", "DOCH", "PADA", "PSKT", "MINA",
    "BULL", "EMTK", "SCMA", "MNCN", "VIVA", "IPTV", "FILM", "SOTS", "MTMG",
    
    # === PLANTATION & AGRI ===
    "AALI", "LSIP", "SGRO", "SIMP", "SSMS", "TBLA", "TAPG", "DSNG", "JARR",
    
    # === TRANSPORTATION & LOGISTICS ===
    "GIAA", "BIRD", "ASSA", "SMDR", "TMAS", "RAJA", "HELI", "RIGS", "MBSS", "SAFE",
    "ARMY", "WEHA", "TAXI",
    
    # === MANUFACTURING & INDUSTRIAL ===
    "ASII", "AUTO", "GJTL", "SMSM", "IMAS", "INDS", "BRAM", "GDYR", "LPIN", "MASA",
    "PBRX", "RICY", "STAR", "KBLI", "KBLM", "VOKS", "JECC", "IKBI", "SCCO",
    "INTP", "SMGR", "AMFG", "ARNA", "TOTO", "MARK", "CAKK", "IKAI", "MLIA",
    "INKP", "TKIM", "FASW", "KDSI", "SPMA",
    
    # === HEALTHCARE ===
    "SILO", "MIKA", "HEAL", "PRDA", "SAME", "BMHS",
    
    # === MISC / PENNY STOCKS ===
    "HADE", "MKNT", "WMPP", "IPPE", "TOYS", "SUPR", "FUJI", "PPRI", "ITIC",
    "CPGT", "CENT", "OCAP", "TRAM", "MAGP", "GZCO", "UNSP", "CNKO",
    "BWPT", "PCAR", "GHON", "BAPI", "SGER", "PURE", "REAL", "MYRX",
    "TGRA", "WICO", "ALTO", "BTEK", "CINT", "DAJK", "SHIP", "SMKL",
    "POOL", "PRAY", "MPMX", "BNBR", "LPGI", "ABMM", "NELY", "BSML",
    "PDES", "GEMA", "CASS", "WOMF", "NICK", "BPII", "PLAS", "HDFA",
    "PPGL", "MFIN", "CFIN", "ADMF", "BFIN", "TIFA", "DEFI", "VRNA",
    "BNBA", "APIC", "UFOE", "TRJA", "CMNT", "MARI", "BUDI", "SOHO",
    "BSWD", "ITIC", "RMKE", "MCAS", "DRMA", "TOOL", "CITA", "DKFT",
    "PEHA", "AMAN", "PSGO", "TUGU", "PNLF", "TRIM", "LPPS", "AMOR",
    
    # === NEW POPULAR (MAY 2026) ===
    "DYAN", "KOPI", "KJEN", "NEST", "DFAM", "BLUE", "BPTR", "CCSI", "ESTI",
    "ZATA", "GRIA", "IRSX", "BELL", "BIPI", "MEDS", "HUMI", "KOTA", "WBSA", "MSIE"
]

# Remove duplicates
idx_tickers = list(set(idx_tickers))
idx_tickers.sort()

print(f"Total unique tickers to check: {len(idx_tickers)}")
print("=" * 60)

results = []
errors = []

# Process in batches of 50 for efficiency
batch_size = 50
for i in range(0, len(idx_tickers), batch_size):
    batch = idx_tickers[i:i+batch_size]
    yf_tickers = [f"{t}.JK" for t in batch]
    ticker_str = " ".join(yf_tickers)
    
    print(f"\nFetching batch {i//batch_size + 1}/{(len(idx_tickers)-1)//batch_size + 1} ({len(batch)} tickers)...")
    
    max_retries = 3
    data = None
    for attempt in range(max_retries):
        try:
            # Use period="1mo" to ensure we get at least 20 trading days
            data = yf.download(ticker_str, period="1mo", progress=False, threads=True)
            if not data.empty:
                break
        except Exception as e:
            err_msg = str(e)[:100]
            print(f"  Attempt {attempt+1} error: {err_msg}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s...
            else:
                errors.append(f"Batch {i//batch_size + 1} error: {err_msg}")
    
    if data is None or data.empty:
        print("  No data returned for this batch after retries.")
        for t in batch:
            errors.append(f"{t}: timeout after 3 retries")
        continue

    for ticker in batch:
        yf_ticker = f"{ticker}.JK"
        try:
            if len(batch) == 1:
                # Single ticker - different structure
                close_series = data['Close']
                volume_series = data['Volume']
            else:
                if yf_ticker in data['Close'].columns:
                    close_series = data['Close'][yf_ticker]
                    volume_series = data['Volume'][yf_ticker]
                else:
                    continue
            
            # Drop NaNs
            close_series = close_series.dropna()
            volume_series = volume_series.dropna()
            
            if len(close_series) == 0:
                continue
                
            close_price = float(close_series.iloc[-1])
            
            if close_price > 0 and close_price < 1000:
                # Calculate avg_transaction_value_20
                last_20_closes = close_series.tail(20)
                last_20_volumes = volume_series.tail(20)
                
                if len(last_20_closes) > 0:
                    transaction_values = last_20_closes * last_20_volumes
                    avg_transaction_value_20 = float(transaction_values.mean())
                else:
                    avg_transaction_value_20 = 0.0
                    
                # Determine tier_eligible
                tier_eligible = []
                if 50 <= close_price < 1000:
                    tier_eligible = ["SCALP_GORENGAN", "BANDAR_SWING"]
                    
                results.append({
                    "ticker": ticker,
                    "price": close_price,
                    "avg_transaction_value_20": avg_transaction_value_20,
                    "tier_eligible": tier_eligible
                })
                print(f"  [OK] {ticker}: Rp{close_price:.0f} | Val: Rp{avg_transaction_value_20:,.0f}")
                
        except Exception as e:
            err = f"{ticker}: {str(e)[:100]}"
            print(f"  Error processing {ticker}: {err}")
            errors.append(err)
    
    # Small delay to avoid rate limiting
    time.sleep(0.5)

# Sort by price descending
results.sort(key=lambda x: x['price'], reverse=True)

print("\n" + "=" * 60)
print(f"\n[RESULT] TOTAL EMITEN HARGA < 1000 IDR: {len(results)}")
print("=" * 60)

# Save results to JSON
output = {
    "date": date.today().isoformat(),
    "total": len(results),
    "stocks": results,
    "errors": errors
}

output_file = os.path.join(os.path.dirname(__file__), "idx_prices_v2.json")
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n[SAVED] Results saved to {output_file}")
