# OTrade Ultra Advanced Trading Bot

OTrade is an ultra-advanced trading bot designed for MetaTrader 5 on Linux. It features a self-learning neural brain, multi-timeframe analysis, and AI-driven decision making using OpenAI GPT-4o.

## Features

- Multi-Timeframe Analysis: M1 to MN1 analysis for robust market insights.
- Neural Brain: Integrated SQL-based memory and self-learning pattern recognition.
- AI Decision Making: Uses GPT-4o to synthesize market data and execute trades.
- Risk Management: Advanced position sizing and trailing stop mechanisms.
- Headless Operation: Designed to run on Linux servers using Wine and Xvfb.

## Prerequisites

- Linux OS (Ubuntu 22.04 or later recommended).
- Wine installed and configured.
- Python 3.10 or later.
- Xvfb for headless MT5 execution.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kingtechies/otrade.git
   cd otrade
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   Required variables:
   - OPENAI_API_KEY
   - MT5_LOGIN
   - MT5_PASSWORD
   - MT5_SERVER

## Running the Bot

To start the bot and the MT5 terminal in headless mode, run the provided start script:

```bash
./start_trading.sh
```

The script will:
1. Start a virtual display (Xvfb).
2. Launch MetaTrader 5 via Wine.
3. Initialize the RPyC bridge server.
4. Start the Python trading bot.

## Manual MT5 Access

If you need to access the MT5 GUI (e.g., for initial login or configuration), you can use VNC:

1. Start a VNC server on the virtual display:
   ```bash
   x11vnc -display :99 -nopw -forever &
   ```
2. Connect using a VNC viewer to `localhost:5900`.

## Architecture

- main.py: Entry point and core trading loop.
- ai_brain.py: GPT-4o integration for market analysis.
- neural_brain.py: Self-learning and pattern memory system.
- mtf_analyzer.py: Technical analysis across multiple timeframes.
- risk_manager.py: Risk calculation and position management.
- mt5_connector.py: Bridge between Python and MT5 via RPyC.
