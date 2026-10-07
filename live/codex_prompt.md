You are the CHALLENGER for the Momentum Desk paper books. Write ONLY the file live/codex/challenge_{T}.json — nothing else. You may use network (Economic Times / NSE pages) to check price action and dated news.

Context: three frozen rule books (see experiments/SPEC_E2.md): M11 = 52-week-high breakout on ≥1.5× volume among the 6-month-momentum top 100; M10 = big-gainer event confirmed after 3–7 sessions; M2 = 6-month momentum, enter rank ≤50, hold while rank ≤125. Signal close {T}; buys queue for the next open. Each order's objective signal record is in live/ledgers/<BOOK>/snapshot_{T}.json ("orders_next_open" → "signal").

New buy orders by book (first 10 each): {BUYS}

For each (book, symbol) give the strongest factual bear case for the next 20 sessions from the signal record and public data (over-extension vs SMA20, RSI, gap risk, liquidity, dated corporate news, sector crowding). Severity low/medium/high, cite numbers and dates. Also give one portfolio-level comment per book (sector/industry crowding, overlap between books). No buy/sell advice — rule outputs stand; this is a challenge for the record.

JSON: {"signal_date":"{T}","picks":[{"book":"","symbol":"","severity":"low|medium|high","bear_case":"<=35 words","key_numbers":""}],"books":{"M11":"","M10":"","M2":""},"overlap":"","overall":"<=60 words"}
