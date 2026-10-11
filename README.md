# Arise v0.1
Android automation app (Kivy + Python + a small Java notification listener).

## Build the APK (no installs needed)
1. Create a free GitHub repo and upload ALL files in this folder (keep the .github folder).
2. Open the repo > Actions tab > "Build Arise APK" (it runs on every push; first build ~20-30 min).
3. When it finishes, open the run and download the `arise-apk` artifact (zip) > unzip > install the .apk.

## First run on the phone
1. Create a PIN. 2. Settings tab: paste your YouTube playlist link. 3. Auto-reply tab: Grant notification access
(Android may need "Allow restricted settings" in App info > menu). 4. Allow SMS permission when asked.

## Windows .exe
The same repo builds `Arise.exe` (Actions > arise-windows-exe). Voice input, steps, GPS, calls and focus
blocking are phone-only; on PC you can type commands and get spoken answers + AI chat.

## AI key
Never put your key in the code. Paste it in the app: Settings > AI API key.
