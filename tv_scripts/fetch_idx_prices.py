"""
Fetch all IDX stock prices from Yahoo Finance and filter those below 1000 IDR.
Output: sorted list of tickers with their latest prices.
"""
import yfinance as yf
import json
import time
import os

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
    # Convert to Yahoo Finance format
    yf_tickers = [f"{t}.JK" for t in batch]
    ticker_str = " ".join(yf_tickers)
    
    print(f"\nFetching batch {i//batch_size + 1}/{(len(idx_tickers)-1)//batch_size + 1} ({len(batch)} tickers)...")
    
    try:
        data = yf.download(ticker_str, period="1d", progress=False, threads=True)
        
        if data.empty:
            print(f"  No data returned for this batch")
            continue
            
        for ticker in batch:
            yf_ticker = f"{ticker}.JK"
            try:
                if len(batch) == 1:
                    # Single ticker - different structure
                    close_price = data['Close'].iloc[-1]
                else:
                    if yf_ticker in data['Close'].columns:
                        close_price = data['Close'][yf_ticker].iloc[-1]
                    else:
                        continue
                
                if close_price is not None and not (close_price != close_price):  # not NaN
                    close_price = float(close_price)
                    if close_price < 1000 and close_price > 0:
                        results.append({
                            "ticker": ticker,
                            "price": close_price
                        })
                        print(f"  [OK] {ticker}: Rp{close_price:.0f}")
            except Exception as e:
                pass
                
    except Exception as e:
        print(f"  Error: {str(e)[:100]}")
        errors.append(str(e)[:100])
    
    # Small delay to avoid rate limiting
    time.sleep(0.5)

# Sort by price descending (most liquid penny stocks tend to have higher volume)
results.sort(key=lambda x: x['price'], reverse=True)

print("\n" + "=" * 60)
print(f"\n[RESULT] TOTAL EMITEN HARGA < 1000 IDR: {len(results)}")
print("=" * 60)

# Group into batches of 10
batches = []
for i in range(0, len(results), 10):
    batch = results[i:i+10]
    batches.append(batch)

for idx, batch in enumerate(batches):
    print(f"\n--- BATCH {chr(65+idx)} ({len(batch)} emiten) ---")
    for item in batch:
        print(f"  {item['ticker']:8s} Rp{item['price']:>7.0f}")

# Save results to JSON
output = {
    "date": "2026-05-12",
    "total": len(results),
    "batches": len(batches),
    "stocks": results,
    "batch_groups": {
        f"batch_{chr(65+i)}": [s['ticker'] for s in batch]
        for i, batch in enumerate(batches)
    }
}

output_file = os.path.join(os.path.dirname(__file__), "idx_below_1000.json")
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n[SAVED] Results saved to {output_file}")
print(f"[TOTAL] {len(results)} emiten in {len(batches)} batches of 10")
