# Contributing to AI Trading Journal

We welcome contributions! Please follow these guidelines to ensure a smooth collaboration process.

## Development Workflow

1.  **Fork and Clone**: Fork the repo and clone it locally.
2.  **Environment Setup**:
    ```bash
    uv sync
    source .venv/bin/activate
    ```
3.  **Create a Branch**: Use descriptive branch names (e.g., `feat/gex-calc-optimization`, `fix/ui-glitch`).
4.  **Coding Standards**:
    - Follow **PEP 8**.
    - Use **Type Hints** for all function signatures.
    - Ensure all new features have accompanying **Unit Tests**.
    - Run tests before committing: `uv run pytest`.
5.  **Commit Messages**: Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat: add IV percentile`, `fix: handle missing API data`).

## Project Structure

- `src/`: Core business logic and services.
- `pages/`: Streamlit page entry points.
- `tests/`: Unit and integration tests.
- `specs/`: Feature specifications and planning documents.

## Pull Request Process

1.  Ensure your code passes all tests.
2.  Update documentation if you changed APIs or features.
3.  Submit a PR with a clear description of the changes and any relevant screenshots.
