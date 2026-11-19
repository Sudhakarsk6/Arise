# Example Arise scripts (31)

**In the new app:** Automations > Scripts > *Example library* > pick one > *Add this script* > review > *Approve and enable*.
**In any version:** copy a script's text, paste it in the paste box, tap *Validate and import*, then approve.
Edit the CONSTANTS at the top first (number, city, address, amounts).

Network scripts need the host added under Settings > *Domains scripts may call* (https only):
`api.open-meteo.com`, `air-quality-api.open-meteo.com`, `api.frankfurter.app`, `api.coingecko.com`, `en.wikipedia.org`.

| Category: script | What it does | Permissions |
|---|---|---|
| Finance: Bitcoin price (voice) | Speaks the current Bitcoin price (CoinGecko, free, no key). | network, speak |
| Finance: Currency rate (voice) | Speaks today's exchange rate, e.g. 1 USD in INR (Frankfurter, free, no key). | network, speak, notify |
| Finance: EMI calculator | Monthly loan EMI and total interest, spoken aloud. | speak |
| Finance: Savings tracker | Each run adds an amount to your saved total (remembered between runs) and speaks your progress. | speak, storage |
| Finance: Split the bill | Calculates each person's share, including a tip, and speaks it. | speak |
| General: Google search | Opens a Google search for the words you set. | open_url |
| General: Navigate home | Opens Google Maps with directions to your home address. | open_url |
| General: Open Spotify | Opens the Spotify app. | open_app |
| General: Open YouTube | Opens the YouTube app. | open_app |
| General: Play my YouTube playlist | Opens your YouTube playlist (change PLAYLIST_ID to yours). | open_url |
| General: Sunrise and sunset (voice) | Speaks today's sunrise and sunset times for your city (Open-Meteo, free). | network, speak |
| General: Time and date (voice) | Speaks the current time and today's date. | speak |
| General: Wikipedia summary (voice) | Reads the first two sentences about a topic you set (Wikipedia, free). | network, speak |
| General: YouTube search | Searches YouTube for the words in QUERY (change them) and speaks a confirmation. | open_url, speak |
| Health: Air quality (voice) | Speaks the current air quality index (AQI) for your city (Open-Meteo, free). | network, speak, notify |
| Health: BMI calculator | Works out your BMI from the height and weight you set, and speaks the result. | speak |
| Health: Bedtime reminder | Tells you it is time to wind down. Schedule it: daily 22:30. | notify, speak |
| Health: Daily streak counter | Run it once a day: counts your consecutive days and your best streak. | notify, storage |
| Health: Medicine reminder | Reminds you to take the medicines you list. Schedule it: daily 09:00. | notify, speak |
| Health: Stretch break reminder | Sends a different stretch tip each time. Schedule it: every 45 min. | notify |
| Health: Water reminder | Counts your glasses of water today and reminds you. Schedule it: every 60 min. | notify, storage |
| Productivity: Add calendar event | Opens Google Calendar with an event for tomorrow 09:00-10:00 ready to save. | open_url |
| Productivity: Countdown to a date | Tells you how many days are left until an event (exam, trip, birthday). | speak, notify |
| Productivity: Daily quote (voice) | Speaks and shows a different motivational line every day. | speak, notify |
| Productivity: Gmail compose | Opens a Gmail draft with the recipient, subject and text already filled in. | open_url |
| Productivity: Good morning briefing | Speaks a greeting, today's date and the weather. Schedule it: daily 07:30. | network, speak |
| Productivity: Open Gmail | Opens the Gmail app. | open_app |
| Productivity: Weather report (voice) | Speaks the current weather for your city (Open-Meteo, free, no key). | network, speak, notify |
| Social: Birthday check | Reminds you of birthdays that fall today. Schedule it: daily 08:00. | notify, speak |
| Social: Telegram share | Opens Telegram's share screen with your message ready - pick the chat and send. | open_url |
| Social: WhatsApp message | Opens a WhatsApp chat with your message already typed - you just tap Send. | open_url |

Limits: scripts cannot send WhatsApp/Gmail/Telegram messages by themselves (those apps do not allow it) and cannot
read your inbox; they open the message ready and you press Send. A script may run for about 20 seconds.
