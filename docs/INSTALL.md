# Installation guide

## Android (APK)
1. Open the repo's **Releases** page and download `arise-0.2.0-arm64-v8a-debug.apk`.
2. Allow *Install unknown apps* for your browser/file manager. If Google Play Protect blocks it
   (Arise asks for notification and accessibility access), open Play Store > Play Protect > gear and
   switch scanning off while installing.
3. First run: create a PIN. Then grant what you want to use: Physical activity (steps), SMS/Calls
   (voice commands), Notification access (auto-reply), Accessibility "Arise Focus" (app blocking).
   Android may require *Settings > Apps > Arise > Allow restricted settings* first.

## Windows (.exe) / macOS / Linux from source
```bash
git clone https://github.com/Sudhakarsk6/Arise.git && cd Arise
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install "kivy[base]==2.3.0" plyer pyaes certifi
python main.py
```
The Windows `.exe` is built by the `exe` job in GitHub Actions (artifact `arise-windows-exe`).
It is best-effort and untested on a real Windows machine.

## iOS
Not supported: iOS forbids apps from controlling other apps and from running arbitrary background
automation. The adapter (`arise/adapters/ios.py`) explains this and is the place to add Shortcuts support.

## Run the tests
```bash
pip install pytest pyaes certifi && python -m pytest -q tests
```
