# AI Trading Journal

A privacy-first, AI-powered market structure analysis tool designed for retail traders. This application focuses on Gamma Exposure (GEX), Max Pain, and Volatility analysis, providing institutional-grade metrics with a local-first architecture.

## 🚀 Key Features

- **GEX Sentinel Watchlist**: Real-time monitoring of Gamma Exposure and market structure.
- **Privacy-First Architecture**: All data is stored locally in SQLite. No external server uploads.
- **AI-Powered Analysis**: Integrated LLM support for interpreting complex market structures.
- **High Performance**: Aggressive caching and optimized calculations for low-latency updates.
- **Volatility Visualizations**: Interactive charts for Call/Put walls, OI distribution, and IV skews.

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Framework**: Streamlit
- **Data Source**: yfinance
- **Database**: SQLite
- **Dependency Management**: uv

## 🏁 Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (fast Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-trading-journal.git
   cd ai-trading-journal
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (if applicable)
   ```

4. **Run the Application**
   ```bash
   uv run streamlit run pages/6_GEX_Sentinel.py
   ```

## 📄 License

[MIT License](LICENSE)
