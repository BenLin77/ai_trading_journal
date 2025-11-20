# Deployment Guide

This guide covers the installation, configuration, and execution of the AI Trading Journal application.

## 📦 Local Deployment (Recommended)

Since this application is designed with a **Local-First** philosophy for privacy, we recommend running it on your own machine.

### Prerequisites

- **OS**: Linux, macOS, or Windows (WSL2 recommended)
- **Python**: Version 3.11+
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (Required for dependency management)

### Step-by-Step Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/ai-trading-journal.git
    cd ai-trading-journal
    ```

2.  **Initialize Environment**
    We use `uv` for fast, reliable dependency management.
    ```bash
    uv sync
    ```
    This command creates a virtual environment in `.venv` and installs all locked dependencies.

3.  **Configuration**
    Create your local configuration file:
    ```bash
    cp .env.example .env
    ```

    **Environment Variables:**

    | Variable | Description | Default | Required |
    |----------|-------------|---------|----------|
    | `LLM_API_KEY` | API Key for AI analysis (e.g., OpenAI) | None | No (Analysis disabled if missing) |
    | `LLM_API_ENDPOINT` | Custom LLM endpoint URL | https://api.openai.com... | No |
    | `DB_PATH` | Path to SQLite database file | `trading_journal.db` | No |
    | `CACHE_TTL_MARKET_DATA` | Cache duration for live data (seconds) | `300` (5 min) | No |

4.  **Running the Application**
    Start the Streamlit server:
    ```bash
    uv run streamlit run pages/6_GEX_Sentinel.py
    ```
    The app should automatically open in your browser at `http://localhost:8501`.

## 🔧 Troubleshooting

### Common Issues

**1. `ModuleNotFoundError`**
- **Cause**: Virtual environment not activated or dependencies not installed.
- **Fix**: Ensure you run commands with `uv run ...` or activate the venv via `source .venv/bin/activate`.

**2. "Rate Limit Exceeded" (yfinance)**
- **Cause**: Too many requests to Yahoo Finance in a short period.
- **Fix**: The app has built-in caching (`CACHE_TTL_MARKET_DATA`). Wait a few minutes and refresh.

**3. Database Locked**
- **Cause**: Multiple instances of the app trying to write to SQLite simultaneously.
- **Fix**: Ensure only one instance of the app is running.

## ☁️ Cloud Deployment (Optional)

While not the primary target, you can deploy this to Streamlit Community Cloud:

1.  Push your code to GitHub.
2.  Connect your repo to Streamlit Cloud.
3.  **Important**: Add your `.env` secrets (like `LLM_API_KEY`) to the Streamlit Cloud "Secrets" management console. DO NOT commit `.env` to Git.
