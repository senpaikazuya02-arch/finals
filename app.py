from flask import Flask, render_template, request, redirect, url_for, jsonify
import base64
import os, secrets, uuid, sqlite3, io
from datetime import datetime
from PIL import Image
from io import BytesIO
import qrcode
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

cloudinary.config(
    cloud_name="dhc8ckfmc",
    api_key="589785367198677",
    api_secret="3mdsBSxQGOXW51MeGZcjYzB2SKI",
    secure=True
)
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
    photos = data['photos']
    os.makedirs('temp', exist_ok=True)
    local_photos = []


    for idx, photo_data in enumerate(photos):
        img_base64 = photo_data.split(',')[1]
        image = Image.open(BytesIO(base64.b64decode(img_base64))).convert("RGBA")
        image = image.resize((300, 300))
        folder=f"sessions/{session_id}",
        path = f"photo_{idx + 1}.png"
        image.save(path)
        local_photos.append(path)
        template = Image.open("static/textures/photostrip_template.png").convert("RGBA")

        positions = [
            (50, 100),
            (50, 450),
            (50, 800),
            (50, 1150)
        ]

    for i, path in enumerate(local_photos):
        photo = Image.open(path).convert("RGBA")
        template.paste(photo, positions[i], mask=photo)

        final_path = f"temp/final_strip_{session_id}.png"
        template.save(final_path)

        upload_result = cloudinary.uploader.upload(
            final_path,
            folder=f"sessions/{session_id}",
            public_id="final_strip",
            overwrite=True
        )
        final_url = upload_result['secure_url']

        upload_urls = []
        upload_result = cloudinary.uploader.upload(
            f"data:image/png;base64,{img_base64}",
            folder=f"sessions/{session_id}",
            public_id=f"photo_{idx + 1}",
            overwrite=True
        )
        upload_urls.append(upload_result['secure_url'])
        print(f"Uploaded photo {idx + 1} successfully")

    result_url = url_for('download_page', session_id=session_id, _external=True)
    qr = qrcode.make(result_url)
    qr_stream = io.BytesIO()
    qr.save(qr_stream, format='PNG')
    qr_stream.seek(0)
    qr_upload = cloudinary.uploader.upload(
        qr_stream, 
        folder=f"sessions/{session_id}", 
        public_id="qr", 
        resource_type="image",
        invalidate=True
    )
    qr_url = qr_upload['secure_url']
    print("QR URL:", qr_url)

    return jsonify({
        'status': 'success', 
        'session_id': session_id, 
        'photos': upload_urls, 
        'qr_url': qr_url,
        'final_url': final_url
    })

# Route: Result Page
@app.route("/result/<session_id>")
def result(session_id):
    return render_template("result.html", session_id=session_id)

# Route: Download Page
@app.route('/download/<session_id>')
def download_page(session_id):
    photo_urls = [
        f"https://res.cloudinary.com/dhc8ckfmc/image/upload/v1/sessions/{session_id}/photo_1.png",
        f"https://res.cloudinary.com/dhc8ckfmc/image/upload/v1/sessions/{session_id}/photo_2.png",
        f"https://res.cloudinary.com/dhc8ckfmc/image/upload/v1/sessions/{session_id}/photo_3.png",
        f"https://res.cloudinary.com/dhc8ckfmc/image/upload/v1/sessions/{session_id}/photo_4.png"
    ]
    final_url = f"https://res.cloudinary.com/dhc8ckfmc/image/upload/sessions/{session_id}/final_strip.png"
    return render_template("download.html", session_id=session_id, photos=photo_urls, final_url=final_url)

# Route: Reset to Homepage
@app.route("/reset")
def reset():
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)
