# Arise v0.2 (MyLife AI)

Personal automation, tracking, finance and AI assistant. One Python/Kivy code base for Android (APK) and Windows/macOS/Linux.

* Splash with your logo (assets/logo.png) -> PIN -> Home with automation cards
* Automation Workspace: import / validate / test / diff / approve / roll back Python scripts (sandboxed)
* Health, Habits, Money trackers - no invented data, missing values shown as unavailable
* Finance: watchlist, indicators, backtest, paper trading (live trading is NOT implemented)
* AI assistant (your own key, encrypted with your PIN), voice commands, Focus mode, auto-reply
* Encrypted backups, audit log, rate limiting, auto-lock

Docs: [docs/INSTALL.md](docs/INSTALL.md) | [docs/DEPLOY.md](docs/DEPLOY.md) | [docs/FEATURES.md](docs/FEATURES.md)

Build: push to `main` -> GitHub Actions runs tests, builds the APK and publishes it under **Releases**.
Tests: `pip install pytest pyaes certifi && python -m pytest -q tests`
