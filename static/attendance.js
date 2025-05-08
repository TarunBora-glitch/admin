const video = document.getElementById('video');
const startCamera = document.getElementById('startCamera');
const stopCamera = document.getElementById('stopCamera');
const markAttendance = document.getElementById('markAttendance');
const statusText = document.getElementById('status');
const goToDashboard = document.getElementById('goToDashboard');
// const subjectSelect = document.getElementById('subjectSelect');

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
    window.location.href = '/student_dashboard'; 
});


// Mark attendance
markAttendance.addEventListener('click', async () => {
    // Collect form values
    const fullName = document.getElementById('fullName').value;
    const rollNumber = document.getElementById('rollNumber').value;
    const branch = document.getElementById('branchSelect').value;
    const semester = document.getElementById('semesterSelect').value;
    const subject = document.getElementById('subjectSelect').value;

    // Check if all fields are filled
    if (!fullName || !rollNumber || !branch || !semester || !subject) {
        statusText.innerText = "Status: All fields are required.";
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
            body: JSON.stringify({
                full_name: fullName,
                roll_number: rollNumber,
                branch: branch,
                semester: semester,
                subject_name: subject,
                image: imageData
            })
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
    }, 2000);
});
document.getElementById('rollNumber').addEventListener('blur', fetchStudentDetails);
document.getElementById('fullName').addEventListener('blur', fetchStudentDetails);
async function fetchStudentDetails() {
    const fullName = document.getElementById('fullName').value.trim();
    const rollNumber = document.getElementById('rollNumber').value.trim();
    const branchSelect = document.getElementById('branchSelect');
    const semesterSelect = document.getElementById('semesterSelect');
    const subjectSelect = document.getElementById('subjectSelect');

    if (!fullName || !rollNumber) return;

    try {
        const response = await fetch('/api/student_info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullName, roll_number: rollNumber })
        });

        const data = await response.json();

        if (!data.found) {
            // Show "Student not found" in all dropdowns
            branchSelect.innerHTML = '<option value="">Student not found</option>';
            semesterSelect.innerHTML = '<option value="">Student not found</option>';
            subjectSelect.innerHTML = '<option value="">Student not found</option>';
            return;
        }

        // Populate Branch with a default option + actual value
        branchSelect.innerHTML = '<option value="">-- Select Branch --</option>';
        const branchOption = document.createElement('option');
        branchOption.value = data.branch;
        branchOption.textContent = data.branch;
        branchSelect.appendChild(branchOption);

        // Populate Semester with a default option + actual value
        semesterSelect.innerHTML = '<option value="">-- Select Semester --</option>';
        const semOption = document.createElement('option');
        semOption.value = data.semester;
        semOption.textContent = data.semester;
        semesterSelect.appendChild(semOption);

        // Populate Subjects
        subjectSelect.innerHTML = '<option value="">-- Select Subject --</option>';
        data.subjects.forEach(subject => {
            const option = document.createElement('option');
            option.value = subject;
            option.textContent = subject;
            subjectSelect.appendChild(option);
        });

    } catch (error) {
        console.error("Error fetching student info:", error);
        branchSelect.innerHTML = '<option value="">Error fetching data</option>';
        semesterSelect.innerHTML = '<option value="">Error fetching data</option>';
        subjectSelect.innerHTML = '<option value="">Error fetching data</option>';
    }
}
