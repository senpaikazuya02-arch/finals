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
  countdownEl.style.display = 'block';
  countdownEl.innerText = timeLeft;

  const countdown = setInterval(() => {
    timeLeft--;
    countdownEl.innerText = timeLeft;

    if (timeLeft === 0) {
      clearInterval(countdown);
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
      <img src="${dataURL}" width="160" class="preview-img">
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
  // TODO: send `photos[]` to Flask via fetch POST
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

      // After retake, show "Done" again and hide ongoing text
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
  fetch(`/save_session/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      photos: photos
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.status === 'success') {
      console.log('Cloudinary URLs received:', {
        photos: data.photos,
        qr_url: data.qr_url
      });
      
      // Store URLs with timestamp to avoid cache issues
      const timestamp = new Date().getTime();
      localStorage.setItem('photoUrls', JSON.stringify(data.photos));
      localStorage.setItem('qrUrl', `${data.qr_url}?t=${timestamp}`);
      
      // Immediate redirect
      window.location.href = `/result/${sessionId}`;
    } else {
      throw new Error(data.message || 'Unknown server error');
    }
  })
  .catch(error => {
    console.error('Session save failed:', error);
    alert('Failed to save session: ' + error.message);
    document.getElementById('loadingIndicator').style.display = 'none';
  });
}
