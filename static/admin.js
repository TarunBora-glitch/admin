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
    const name = document.getElementById('searchName').value;
    const roll = document.getElementById('searchRollNumber').value;
    const subject = document.getElementById('searchSubject').value;
    const date = document.getElementById('searchDate').value;
    const status = document.getElementById('statusFilter').value;

    const params = new URLSearchParams();

    if (name) params.append("full_name", name);
    if (roll) params.append("roll_number", roll);
    if (subject) params.append("subject_name", subject);
    if (date) params.append("date", date);
    if (status) params.append("status", status);

    const exportUrl = `/export_csv?${params.toString()}`;
    window.location.href = exportUrl;
}


