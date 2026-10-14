# PhotoZ

PhotoZ is a web photobooth made with Flask. A student makes a personal QR code, scans it at the booth, takes four photos, and gets a photo strip they can download on their phone.

## How it works

1. The student opens the /qr page, types their student ID and surname, and gets a QR code.
2. At the booth, they open the /scan page and show the QR code to the camera.
3. They take four photos and press Done.
4. The app makes the photo strip, saves everything to Cloudinary, and shows a QR code.
5. Scanning that QR code opens the download page on their phone.

## What it uses

Python, Flask, Pillow, qrcode, Cloudinary, FFmpeg, and SQLite.

## How to run it on your computer

1. Install Python 3.12 and FFmpeg.
2. Open the project folder in a terminal.
3. Create a virtual environment: python -m venv venv
4. Turn it on: venv\Scripts\activate
5. Install the packages: python -m pip install -r requirements.txt
6. Create a file named .env in the project folder and add these three lines, using your own values from Cloudinary (Settings > API Keys, use the key and secret from the same row):

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

7. Check that the keys work: python -c "import os, cloudinary, cloudinary.api; from dotenv import load_dotenv; load_dotenv(); cloudinary.config(cloud_name=os.environ['CLOUDINARY_CLOUD_NAME'], api_key=os.environ['CLOUDINARY_API_KEY'], api_secret=os.environ['CLOUDINARY_API_SECRET']); print(cloudinary.api.ping())"
   It should print {'status': 'ok'}. If it says api_secret mismatch, copy the key and secret again.
8. Start the app: python app.py
9. Open http://127.0.0.1:5000 in Chrome or Edge.

Flask only reads the .env file when it starts, so stop the app with Ctrl+C and start it again after you change the keys.

## Keeping your keys safe

- Never share or upload your .env file. It holds your secret keys.
- Never type the keys into app.py. They are loaded from .env.
- Do not show your key or secret in screenshots or chats. Crop or cover those lines first. If you need help, share only the last line of an error.
- If a key was ever shown or uploaded by mistake, make a new one: go to Cloudinary > Settings > API Keys, generate a new key pair, delete the old one, and update .env.
- Keep .env, venv, temp, database.db, and test files out of GitHub by listing them in .gitignore. If a file is already on GitHub, stop tracking it with: git rm --cached filename
- database.db holds student IDs and surnames, so keep it private.

## Putting it online

The app can run on a host like Render. The host pulls the code from GitHub and runs it.

- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app --timeout 120
- Python version: 3.12
- The .env file is not uploaded, so add CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in the host's Environment settings.
- When you change the Cloudinary key or secret, update them in the host settings too. The site restarts after you save.
- The camera needs HTTPS, which these hosts provide.
- Some hosts do not include FFmpeg. The photo strip still works, but the video strip will not.
- The server disk can reset when the site redeploys, so database.db may be wiped. Photos and videos stay safe in Cloudinary.

## Notes

- The camera only works on 127.0.0.1 or on a site with HTTPS.
- If the video strip does not work, FFmpeg is probably not installed.
- If the Done button fails, check the terminal for the error message.