const video = document.getElementById('video');
const startCamera = document.getElementById('startCamera');
const stopCamera = document.getElementById('stopCamera');
const markAttendance = document.getElementById('markAttendance');
const statusText = document.getElementById('status');
const goToDashboard = document.getElementById('goToDashboard');
const subjectSelect = document.getElementById('subjectSelect');

let stream;

// Start the camera
startCamera.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        markAttendance.disabled = false;
        startCamera.disabled = true;
        stopCamera.disabled = false;
    } catch (error) {
        console.error("Camera access error:", error);
        statusText.innerText = "Status: Unable to access camera.";
    }
});

// Stop the camera
stopCamera.addEventListener('click', () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    video.srcObject = null;
    markAttendance.disabled = true;
    startCamera.disabled = false;
    stopCamera.disabled = true;
});

// Redirect to dashboard
goToDashboard.addEventListener('click', () => {
    window.location.href = '/student_dashboard'; // Update if your dashboard URL is different
});

// Populate the subject dropdown
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/get_subjects');
        const subjects = await response.json();

        if (Array.isArray(subjects)) {
            subjectSelect.innerHTML = '<option value="">-- Select a subject --</option>';
            subjects.forEach(subject => {
                const option = document.createElement('option');
                option.value = subject.id;
                option.textContent = subject.name;
                subjectSelect.appendChild(option);
            });
        } else {
            alert('Error loading subjects: ' + (subjects.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error loading subjects: ' + error.message);
    }
});

// Mark attendance
markAttendance.addEventListener('click', async () => {
    const subjectId = subjectSelect.value;

    if (!subjectId || subjectId === "0") {
        statusText.innerText = "Status: Please select a valid subject.";
        return;
    }

    statusText.innerText = 'Status: Recognizing face...';

    // Capture image from video
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL('image/jpeg');
    console.log("Captured Image Data:", imageData);

    try {
        const response = await fetch('/mark_attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData, subject_id: subjectId })
        });

        const result = await response.json();
        const message = result.message || "No response received.";
        let formattedMessage = "";

        if (message.includes("Attendance marked for subject")) {
            const subject = message.split("Attendance marked for subject ")[1].replace('.', '');
            formattedMessage = `Status: Attendance marked for subject <span class="green-subject">${subject}</span>.`;
        } else if (message.includes("Attendance for subject") && message.includes("already marked today")) {
            const subject = message.split("Attendance for subject ")[1].split(" already")[0];
            formattedMessage = `Status: Attendance for subject <span class="red-subject">${subject}</span> already exists today.`;
        } else {
            formattedMessage = `Status: <span class="gray-text">${message}</span>`;
        }

        statusText.innerHTML = formattedMessage;

    } catch (error) {
        console.error("Error marking attendance:", error);
        statusText.innerText = "Status: Error occurred while marking attendance.";
    }

    // Reset status
    setTimeout(() => {
        statusText.innerText = 'Status:';
    }, 3000);
});
