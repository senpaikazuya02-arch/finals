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

cloudinary.uploader.upload(
    "static/textures/camera_icon.png",  # use an actual image path
    folder="sessions/test-folder",
    public_id="photo_test"
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
    try:
        data = request.get_json()
        photos = data['photos']

        # Upload photos
        upload_urls = []
        for idx, photo_data in enumerate(photos):
            # Ensure the photo data is properly formatted
            if not photo_data.startswith('data:image/'):
                raise ValueError(f"Invalid image data format for photo {idx + 1}")
                
            img_base64 = photo_data.split(',')[1]
            upload_result = cloudinary.uploader.upload(
                f"data:image/png;base64,{img_base64}",
                folder=f"sessions/{session_id}",
                public_id=f"photo_{idx + 1}",
                overwrite=True,
                invalidate=True  # Force cache refresh
            )
            upload_urls.append(upload_result['secure_url'])

        # Generate QR code
        result_url = url_for('download_page', session_id=session_id, _external=True)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(result_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Upload QR with explicit settings
        qr_upload = cloudinary.uploader.upload(
            img_bytes,
            folder=f"sessions/{session_id}",
            public_id="qr_code",
            resource_type="image",
            format="png",
            invalidate=True,
            quality="auto:best"
        )
        
        # Construct URL with version parameter
        qr_url = cloudinary.CloudinaryImage(
            f"sessions/{session_id}/qr_code"
        ).build_url(version=qr_upload['version'])
        
        # Verify the URL is accessible
        if not verify_cloudinary_url(qr_url):
            raise ValueError("Generated QR URL is not accessible")

        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'photos': upload_urls,
            'qr_url': qr_url
        })

    except Exception as e:
        app.logger.error(f"Error in save_session: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'stacktrace': traceback.format_exc()
        }), 500

def verify_cloudinary_url(url):
    """Verify that a Cloudinary URL is accessible"""
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False


# Route: Result Page
@app.route("/result/<session_id>")
def result(session_id):
    return render_template("result.html", session_id=session_id)

# Route: Download Page
@app.route('/download/<session_id>')
def download_page(session_id):
    return render_template("download.html", session_id=session_id)

# Route: Reset to Homepage
@app.route("/reset")
def reset():
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)
