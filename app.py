from flask import Flask, render_template, request, redirect, url_for, jsonify, base64
import os, secrets, uuid, sqlite3
from datetime import datetime
from PIL import Image
from io import BytesIO
import qrcode

app = Flask(__name__)

# Route: Homepage 
@app.route("/")
def index():
    return render_template("index.html")

# Route: Scan
@app.route("/scan")
def scan():
    return render_template("scan.html")

# Sessions
@app.route('/start_session', methods=['POST'])
def start_session():
    data = request.get_json()
    student_id = data['student_id']
    surname = data['surname']
    session_id = str(uuid.uuid4())

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            student_id TEXT,
            surname TEXT,
            created_at TIMESTAMP
        )
    ''')
    c.execute('INSERT INTO sessions (session_id, student_id, surname, created_at) VALUES (?, ?, ?, ?)',
            (session_id, student_id, surname, datetime.now()))
    conn.commit()
    conn.close()

    return jsonify({ 'session_id': session_id })


# Route: Mode Selection
@app.route("/select")
def select():
    session_id = request.args.get("session_id")
    if not session_id:
        return redirect(url_for("index"))

    return render_template("select.html", session_id=session_id)

# Route: Photobooth UI
@app.route("/photobooth/<session_id>")
def photobooth(session_id):
    return render_template("photobooth.html", session_id=session_id)

# Route: Videobooth UI
@app.route("/videobooth/<session_id>")
def videobooth(session_id):
    return render_template("videobooth.html", session_id=session_id)

@app.route('/save_session/<session_id>', methods=['POST'])
def save_session(session_id):
    data = request.get_json()
    photos = data.get('photos', [])

    folder_path = os.path.join('static', 'results', session_id)
    os.makedirs(folder_path, exist_ok=True)

    # Save each photo
    for idx, photo_data in enumerate(photos):
        photo_bytes = base64.b64decode(photo_data.split(',')[1])
        with open(os.path.join(folder_path, f'photo_{idx+1}.jpg'), 'wb') as f:
            f.write(photo_bytes)

    # TODO: Generate a .mp4 later (can use moviepy)

    # Generate QR Code
    result_url = f"http://localhost:5000/result/{session_id}"  # Change to your domain in prod
    qr = qrcode.make(result_url)
    qr.save(os.path.join(folder_path, 'qr.png'))

    return jsonify({'status': 'success'})

# Route: Result Page
@app.route("/result/<session_id>")
def result(session_id):
    return render_template("result.html", session_id=session_id)

# Route: Reset to Homepage
@app.route("/reset")
def reset():
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)
