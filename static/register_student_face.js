
const video = document.getElementById('video');
const startCamera = document.getElementById('startCamera');
const stopCamera = document.getElementById('stopCamera');
const registerFace = document.getElementById('registerFace');
const statusText = document.getElementById('status');
const inputs = [
  document.getElementById('fullname'),
  document.getElementById('rollno'),
];

let stream = null;

function validateFormAndCamera() {
  const allFilled = inputs.every(input => input.value.trim() !== "");
  const isCameraOn = stream !== null;
  registerFace.disabled = !(allFilled && isCameraOn);
}

inputs.forEach(input => {
  input.addEventListener('input', validateFormAndCamera);
});

startCamera.addEventListener('click', async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    startCamera.disabled = true;
    stopCamera.disabled = false;
    statusText.textContent = "Status: Camera started";
    validateFormAndCamera();
  } catch (err) {
    console.error("Camera error:", err);
    alert("Camera access was denied.");
  }
});

stopCamera.addEventListener('click', () => {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    video.srcObject = null;
    stream = null;
    statusText.textContent = "Status: Camera stopped";
    startCamera.disabled = false;
    stopCamera.disabled = true;
    registerFace.disabled = true;
  }
});

registerFace.addEventListener('click', async () => {
try {
    if (!stream) {
        alert('Please start the camera first!');
        return;
    }

    // Capture the frame and send the image data
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL('image/jpeg');
    console.log("Captured image data:", imageData);  // Debugging the captured image data

    const response = await fetch('/register_face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            fullname: document.getElementById('fullname').value.trim(),
            rollno: document.getElementById('rollno').value.trim(),
            image: imageData
        })
    });


    const result = await response.json();
    alert(result.message);

} catch (error) {
    console.error('Error during face registration:', error);
    alert('Failed to register face.');
}
});
