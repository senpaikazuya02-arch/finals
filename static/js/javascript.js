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

async function finishSession() {
  try {
    // Show loading state immediately
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) loadingIndicator.style.display = 'block';

    const response = await fetch(`/save_session/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ photos: photos })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Server response:', data); // Debug log

    if (data.status === 'success') {
      // Add cache-busting parameter
      const qrUrl = `${data.qr_url}?t=${Date.now()}`;
      
      // Double-verify URL before storing
      const urlValid = await verifyUrl(qrUrl);
      if (!urlValid) {
        throw new Error('QR URL is not accessible');
      }

      // Store in localStorage
      localStorage.setItem('qrUrl', qrUrl);
      console.log('Stored QR URL:', qrUrl); // Debug log

      // Ensure storage is complete before redirect
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Redirect
      window.location.href = `/result/${sessionId}`;
    } else {
      throw new Error(data.message || 'Server returned error status');
    }
  } catch (error) {
    console.error('Session save failed:', error);
    alert(`Error: ${error.message}\nPlease try again.`);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
  }
}

// Helper function to verify URL accessibility
async function verifyUrl(url) {
  try {
    const response = await fetch(url, { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}