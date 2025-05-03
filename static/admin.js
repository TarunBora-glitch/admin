// Admin login form submission
document.getElementById("adminLoginForm").addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(this);

    fetch("/admin-login", {
        method: "POST",
        body: formData
    })
    .then(response => response.text())
    .then(data => {
        if (data.includes("Invalid Credentials")) {
            alert("Invalid login. Try again!");
        } else {
            alert("Login successful");
            window.location.href = "/admin";
        }
    })
    .catch(error => console.error("Error:", error));
});



function exportFilteredCSV() {
    const fullName = document.getElementById('full_name')?.value || '';
    const rollNumber = document.getElementById('roll_number')?.value || '';
    const subjectName = document.getElementById('subject_name')?.value || '';
    const date = document.getElementById('date')?.value || '';
    const status = document.getElementById('status')?.value || '';

    const queryParams = new URLSearchParams({
        full_name: fullName,
        roll_number: rollNumber,
        subject_name: subjectName,
        date: date,
        status: status
    });

    const url = `/export_csv?${queryParams.toString()}`;
    window.location.href = url;  // Triggers download
}

// Show the popup message temporarily (3 seconds)
window.addEventListener('DOMContentLoaded', () => {
    const popup = document.getElementById('popupMessage');
    if (popup) {
        setTimeout(() => {
            popup.style.display = 'none';
        }, 1500); // hide after 3 seconds
    }
});


// Show the No Records Found message for 3 seconds
window.addEventListener('DOMContentLoaded', () => {
    const message = document.getElementById('noRecordsMessage');
    if (message) {
        setTimeout(() => {
            message.style.display = 'none'; // Hide the message after 3 seconds
        }, 1500); // 3 seconds
    }
});

