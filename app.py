from flask import Flask, render_template, request, redirect, url_for, jsonify
import base64
import os, secrets, uuid, sqlite3, io
from datetime import datetime
from PIL import Image
from PIL import ImageOps
from io import BytesIO
import qrcode
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import subprocess
import ffmpeg
import threading


cloudinary.config(
    cloud_name="dhc8ckfmc",
    api_key="589785367198677",
    api_secret="3mdsBSxQGOXW51MeGZcjYzB2SKI",
    secure=True
)
app = Flask(__name__)
app.config['SERVER_NAME'] = 'photoz-qk29.onrender.com'
app.config['PREFERRED_URL_SCHEME'] = 'https'


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
    videos = data.get('videos', [])
    photos = data['photos']
    os.makedirs('temp', exist_ok=True)
    local_photos = []
    upload_urls = []
    template = Image.open("static/textures/photostrip_template.png").convert("RGBA")
    template_width, template_height = template.size

    target_width = 660
    target_height = 390
    gap = 20
    start_y = 30
    center_x = (template_width - target_width) // 2

    positions = []
    for i in range(4):
        y = start_y + i * (target_height + gap)
        positions.append((center_x, y))

    # photo
    for idx, photo_data in enumerate(photos):
        img_base64 = photo_data.split(',')[1]
        image = Image.open(BytesIO(base64.b64decode(img_base64))).convert("RGBA")
        image = center_crop(image, target_width, target_height)        

        path = f"photo_{idx + 1}.png"
        image.save(path)
        local_photos.append(path)

        upload_result = cloudinary.uploader.upload(
            f"data:image/png;base64,{img_base64}",
            folder=f"sessions/{session_id}",
            public_id=f"photo_{idx + 1}",
            overwrite=True
        )
        upload_urls.append(upload_result['secure_url'])
        print(f"Uploaded photo {idx + 1} successfully")

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

    # video
    video_paths = []
    for idx, video_data in enumerate(videos):
        video_base64 = video_data.split(',')[1]
        video_bytes = base64.b64decode(video_base64)

        video_path = f"temp/video_{idx + 1}_{session_id}.webm"
        with open(video_path, 'wb') as f:
            f.write(video_bytes)
        video_paths.append(video_path)

        upload_result = cloudinary.uploader.upload(
            video_path,
            folder=f"sessions/{session_id}",
            public_id=f"video_{idx + 1}",
            resource_type="video",
            overwrite=True
        )
        print(upload_result['secure_url'])
        print(f"Uploaded video {idx + 1} successfully")
        

    if len(video_paths) == 4:
        threading.Thread(
            target=generate_video_strip,
            args=(session_id, video_paths, positions, center_x)
        ).start()
        final_video_url = None 
    else:
        final_video_url = None
        print("Skipping video strip: not all 4 videos available.")

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
        'final_url': final_url,
        'final_video_url': final_video_url
    })

def generate_video_strip(session_id, video_paths, positions, center_x):
    with app.app_context():
        try:
            # Get duration from first video
            probe = ffmpeg.probe(video_paths[0])
            video_duration = float(probe['format'].get('duration', 5.0))
            
            final_video_path = f"temp/video_strip_{session_id}.webm"
            
            # Build inputs
            inputs = [
                ffmpeg.input('static/textures/photostrip_template.png', loop=1, t=video_duration),
                *[ffmpeg.input(path) for path in video_paths]
            ]
            
            # Build filter chain
            scaled_videos = [
                inputs[i+1].filter('scale', 660, 390) 
                for i in range(len(video_paths))
            ]
            
            overlay = inputs[0]
            for i, (video, pos) in enumerate(zip(scaled_videos, positions)):
                overlay = overlay.overlay(video, x=pos[0], y=pos[1])
            
            # Run ffmpeg
            (
                overlay
                .output(final_video_path, 
                       vcodec='libvpx', 
                       pix_fmt='yuv420p',
                       crf=30, 
                       preset='fast',
                       s='707x2000')
                .run(quiet=True, overwrite_output=True)
            )
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                final_video_path,
                folder=f"sessions/{session_id}",
                public_id="final_strip_video",
                resource_type="video",
                overwrite=True
            )
            print("✅ Final video uploaded:", upload_result['secure_url'])
            
        except Exception as e:
            print("❌ Error generating video strip:", str(e))
            
def center_crop(image, target_width, target_height):
    width, height = image.size

    target_ratio = target_width / target_height
    original_ratio = width / height

    if original_ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        image = image.crop((left, 0, left + new_width, height))
    else:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        image = image.crop((0, top, width, top + new_height))

    return image.resize((target_width, target_height), Image.LANCZOS)

# Route: Result Page
@app.route("/result/<session_id>")
def result(session_id):
    return render_template("result.html", session_id=session_id)

# Route: Download Page
@app.route('/download/<session_id>')
def download_page(session_id):
    final_video_url = f"https://res.cloudinary.com/dhc8ckfmc/video/upload/sessions/{session_id}/final_strip_video.webm"
    final_url = f"https://res.cloudinary.com/dhc8ckfmc/image/upload/sessions/{session_id}/final_strip.png"
    return render_template("download.html", session_id=session_id, final_url=final_url, final_video_url=final_video_url)

# Route: Reset to Homepage
@app.route("/reset")
def reset():
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)
