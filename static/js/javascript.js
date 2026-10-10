VANTA.FOG({
  el: "#vanta-bg",
  mouseControls: true,
  touchControls: true,
  gyroControls: false,
  minHeight: 200.00,
  minWidth: 200.00,
  highlightColor: 0x6a65e3,
  midtoneColor: 0xfcfcfc,
  baseColor: 0xededed,
  blurFactor: 0.67,
  speed: 0.90,
  zoom: 0.70
})

window.onload = function() {
  document.getElementById('instructionModal').style.display = 'flex'; 

  // reset start button 
  const startBtn = document.getElementById('startBtn');
  if (startBtn) {
      startBtn.disabled = true;
  }
};

function closeModal() {
  document.getElementById('instructionModal').classList.add('hidden');
  const startBtn = document.getElementById('startBtn');
  startBtn.disabled = false;
}

const video = document.getElementById('camera');
const countdownEl = document.getElementById('countdown');
const canvas = document.getElementById('snapshot');
const context = canvas.getContext('2d');

let currentShot = 0;
const totalShots = 4;
const photos = [];

function startCountdown() {
  document.querySelector('.start-sess-btn').classList.add('hidden');
  document.querySelector('.ongoing-text').classList.remove('hidden');

  currentShot = 0;
  photos.length = 0;
  countdownAndCapture();
}

function countdownAndCapture() {
  let timeLeft = 5;
  startRecording();
  countdownEl.style.display = 'block';
  countdownEl.innerText = timeLeft;

  const countdown = setInterval(() => {
    timeLeft--;
    countdownEl.innerText = timeLeft;

    if (timeLeft === 0) {
      clearInterval(countdown);
      stopRecording();
      countdownEl.style.display = 'none';
      capturePhoto();
    }
  }, 1000);
}

function capturePhoto() {
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const imageData = canvas.toDataURL('image/png');
  photos[currentShot] = imageData;
  showPreview(currentShot, imageData);

  currentShot++;
  if (currentShot < totalShots) {
    setTimeout(() => countdownAndCapture(), 1000); // Wait 1s before next
  } else {
    showFinalActions();
  }
}

function showPreview(index, dataURL) {
  const container = document.getElementById(`preview-${index + 1}`);
  container.innerHTML = `
    <div class="preview-wrapper">
      <img src="${dataURL}" class="preview-img">
      <img src="/static/textures/edit_icon.svg" class="retake-icon" onclick="retakePhoto(${index})" alt="Retake">
    </div>  
  `;
}

function retakePhoto(index) {
  startRetakeCountdown(index);
  document.querySelector('.ongoing-text').classList.remove('hidden');
  document.getElementById('final-buttons').style.display = 'none';
}

function showFinalActions() {
  document.querySelector('.ongoing-text').classList.add('hidden');
  document.getElementById('final-buttons').style.display = 'block';
}

function finishSession() {
  console.log('Finalizing session...');
}

function startRetakeCountdown(index) {
  let timeLeft = 5;
  countdownEl.style.display = 'block';
  countdownEl.innerText = timeLeft;

  const countdown = setInterval(() => {
    timeLeft--;
    countdownEl.innerText = timeLeft;

    if (timeLeft === 0) {
      clearInterval(countdown);
      countdownEl.style.display = 'none';

      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = canvas.toDataURL('image/png');
      photos[index] = imageData;
      showPreview(index, imageData);

      document.getElementById('final-buttons').style.display = 'block';
      document.querySelector('.ongoing-text').classList.add('hidden');
    }
  }, 1000);
}

navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    video.srcObject = stream;
})
  .catch(err => {
    console.error('Error accessing camera', err);
});

function finishSession() {
  return finishSessionAfterRecording();
}

async function finishSessionAfterRecording() {
  await recordingStopped;

  fetch(`/save_session/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      photos: photos,
      videos: videos.filter(video => typeof video === 'string')
    })
  })
  .then(res => {
    if (!res.ok) {
      return res.text().then(body => {
        console.error('Save session response:', body);
        throw new Error('Server error ' + res.status);
      });
    }
    return res.json();
  })
  .then(data => {
    if (data.status === 'success') {
      localStorage.setItem('photoUrls', JSON.stringify(data.photos));
      localStorage.setItem('qrUrl', data.qr_url);
      window.location.href = `/result/${sessionId}`;
    }
  })
  .catch(err => {
    console.error(err);
    alert('Could not save the session. Check the Flask terminal for the error.');
  });
}

let mediaRecorder;
let recordedChunks = [];
let videos = [];
let recordingStopped = Promise.resolve();

function startRecording() {
  recordedChunks = [];
  const recordingIndex = currentShot;
  mediaRecorder = new MediaRecorder(video.srcObject, {
    mimeType: 'video/webm;codecs=vp8'
  });

  recordingStopped = new Promise(resolve => {
    mediaRecorder.onstop = function() {
      const blob = new Blob(recordedChunks, { type: 'video/webm' });
      const reader = new FileReader();
      reader.onloadend = function() {
        if (typeof reader.result === 'string' && blob.size > 0) {
          videos[recordingIndex] = reader.result;
        }
        resolve();
      };
      reader.onerror = resolve;
      reader.readAsDataURL(blob);
    };
  });

  mediaRecorder.ondataavailable = function(e) {
    if (e.data.size > 0) recordedChunks.push(e.data);
  };
  mediaRecorder.start();
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

const qrResultBtn = document.querySelector('.qr-result-btn');
if (qrResultBtn) {
  qrResultBtn.addEventListener('click', () => {
    localStorage.removeItem('qrUrl');
    localStorage.removeItem('photoUrls');
  });
}
