"""
SENTRA AS - Trading Assistant Module (Phase 2, Module 13)
Analyzes simulated stock/crypto trends offline, computes indicators, 
and posts execution order tickets into the Human-in-the-Loop Gateway.
"""

import time
import random
from typing import Dict, List, Any
from sentra_as.database import log_system_event, add_approval_item

def fetch_market_prices() -> Dict[str, List[float]]:
    """
    Simulates high-fidelity market ticker price feeds (BTC, ETH, AAPL)
    to perform local mathematical technical indicator analysis offline.
    """
    # Simulate a 10-day price history
    base_btc = 95000.0
    base_eth = 3100.0
    
    btc_feed = []
    eth_feed = []
    
    # Deterministic price walk
    random.seed(int(time.time() // 86400)) # keeps prices stable for the current day
    for _ in range(10):
        base_btc += random.uniform(-1500, 2000)
        base_eth += random.uniform(-80, 100)
        btc_feed.append(round(base_btc, 2))
        eth_feed.append(round(base_eth, 2))
        
    return {"BTC": btc_feed, "ETH": eth_feed}

def run(command: str = "") -> str:
    """
    Executes algorithmic trade analysis.
    Computes Moving Averages and relative strength triggers, proposing orders to Arsalan's gate.
    """
    log_system_event("TRADING_ASSISTANT", "Fetching sovereign market feeds...")
    prices = fetch_market_prices()
    
    btc_series = prices["BTC"]
    eth_series = prices["ETH"]
    
    # Calculate Simple Moving Averages
    ma5_btc = sum(btc_series[-5:]) / 5.0
    ma10_btc = sum(btc_series) / 10.0
    
    current_btc = btc_series[-1]
    
    log_system_event("TRADING_ASSISTANT", f"BTC Price series compiled. Current: {current_btc} USD. MA-5: {ma5_btc:.2f}")
    
    # Indicator Logic: Golden Cross / Death Cross rules
    if ma5_btc > ma10_btc:
        signal = "BUY"
        reason = "MA-5 crossed above MA-10 (Bullish Momentum)"
    elif ma5_btc < ma10_btc:
        signal = "SELL"
        reason = "MA-5 crossed below MA-10 (Bearish Momentum)"
    else:
        signal = "HOLD"
        reason = "Consolidation zone. Zero crossover."
        
    report = (
        f"=== SENTRA AS ALGORITHMIC TRADING REPORT ===\n"
        f"Analyzed on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- BTC/USD Ticker: {current_btc:,.2f} USD\n"
        f"- 5-Period Moving Avg: {ma5_btc:,.2f}\n"
        f"- 10-Period Moving Avg: {ma10_btc:,.2f}\n"
        f"📊 Strategy Indicator: {signal} ({reason})"
    )
    
    log_system_event("TRADING_ASSISTANT", "Market analysis computed successfully.")
    
    # If a valid Buy/Sell signal is generated, push it to the Human-in-the-Loop holding dock!
    if signal in ("BUY", "SELL"):
        trade_amount = 0.05 if signal == "BUY" else 0.02
        proposal = (
            f"TRADE TICKET: {signal} {trade_amount} BTC @ Limit {current_btc:,.2f} USD\n"
            f"Ref Ticket: TRD-{int(time.time() % 100000)}\n"
            f"Trigger: {reason}"
        )
        
        add_approval_item(
            title=f"Autonomous BTC {signal} Order",
            asset_type="trade",
            content=proposal,
            metadata={
                "pair": "BTC/USD",
                "action": signal,
                "amount": trade_amount,
                "limit_price": current_btc
            }
        )
        log_system_event("TRADING_ASSISTANT", f"Trade ticket pushed to holding gateway: {signal} order.")
        
    return report

if __name__ == "__main__":
    print(run())
