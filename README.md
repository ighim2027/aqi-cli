# aqi-cli

Fetches PM2.5 from OpenAQ, converts to US EPA AQI, prints it color-coded in the terminal.

No dependencies. Python 3.8+.

```bash
python aqi.py --demo                      # offline, canned data
export OPENAQ_API_KEY=...
python aqi.py --lat 40.08 --lon -82.80
```

Free API key at [openaq.org](https://openaq.org).

## The AQI conversion

`pm25_to_aqi()` implements the EPA piecewise-linear index. Breakpoints are the **2024-revised** values, effective May 6, 2024, which lowered the annual PM2.5 NAAQS from 12.0 to 9.0 µg/m³ and moved the upper breakpoints:

| AQI | PM2.5 (µg/m³) | Category |
|---|---|---|
| 50 | 9.0 | Good |
| 100 | 35.4 | Moderate |
| 150 | 55.4 | Unhealthy for Sensitive Groups |
| 200 | 125.4 | Unhealthy |
| 300 | 225.4 | Very Unhealthy |
| 500 | 325.4 | Hazardous |

Source: [Federal Register, 89 FR 16202](https://www.federalregister.gov/documents/2024/03/06/2024-02637/reconsideration-of-the-national-ambient-air-quality-standards-for-particulate-matter) and the [EPA AQI fact sheet](https://www.epa.gov/system/files/documents/2024-02/pm-naaqs-air-quality-index-fact-sheet.pdf).

**If you copy AQI code off the internet, check the breakpoints.** Most of what's out there predates May 2024 and still uses 12.0 for the Good/Moderate line. That code reports Good on days the EPA calls Moderate.

## The truncation is not optional

The concentration gets truncated to one decimal place *before* the lookup:

```python
c = int(conc * 10) / 10.0
```

This is specified in EPA's Technical Assistance Document, not a rounding convenience. A raw reading of 9.04 µg/m³ truncates to 9.0 and is **Good** (AQI 50). If you skip the truncation and let 9.04 fall through, you compute AQI 51 and report **Moderate**. Same air, different color, different public health message.

## What this doesn't do right

The EPA AQI is defined on a **24-hour mean**. This tool prints the latest instantaneous sensor reading through the 24-hour formula, which is not the same thing and will overreact to a passing truck. AirNow handles this with the NowCast algorithm — a weighted average over the last 12 hours that adapts its weighting to how fast concentrations are changing.

Implementing NowCast is the obvious next step and is the difference between a toy and something you'd trust. Until then the tool prints a disclaimer, which is a poor substitute.

## Sanity check

```bash
python -c "
from aqi import pm25_to_aqi
for c in [0.0, 9.0, 9.1, 35.4, 35.5, 55.4, 125.4]:
    print(c, pm25_to_aqi(c))
"
```

Every EPA breakpoint should land on exactly 0/50/51/100/101/150/200.

