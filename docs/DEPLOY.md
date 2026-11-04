# Production deployment guide

**How releases are built:** every push to `main` runs `.github/workflows/build.yml`:
tests -> Buildozer APK (python-for-android `v2024.01.21`, Python 3.11, NDK 25b, API 33) -> a GitHub
Release named `apk-<run number>`. A `build-logs` branch receives a short error summary of each run.

**Before sharing the app with others**
1. Make the repository private (Settings > Danger Zone) if it should not be public.
2. Replace the debug APK by a signed release build: create a keystore, store it and its passwords as
   GitHub *encrypted secrets*, and run `buildozer android release` followed by `apksigner`.
3. Never commit API keys. Users enter their own key in Settings; it is encrypted with their PIN.
4. Back up: Settings > Back up now (passphrase-encrypted). Keep copies off the phone.
5. Play Store distribution needs a Play Console account and justification for the Accessibility and
   Notification-listener permissions; sideloading avoids that.

**Update flow:** edit code -> push to `main` -> wait for the green run -> install the new release APK
(data is kept when the APK is signed with the same key).

**Known production gaps:** the database file is not encrypted (it relies on Android's per-app
sandbox; backups ARE encrypted); live trading and broker integration are intentionally not implemented.
