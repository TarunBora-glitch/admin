document.getElementById("studentLoginForm").addEventListener("submit", function (e) {
    e.preventDefault();
    
    const formData = new FormData(this);

    fetch("/student-login", {
        method: "POST",
        body: formData
    })
    .then(response => response.text())
    .then(data => {
        if (data.includes("Invalid Credentials") || data.includes("User not found")) {  
            alert("Invalid login. Try again!");
        } else {
            alert("Login successful");
            window.location.href = "/student_dashboard";  
        }
    })
    .catch(error => console.error("Error:", error));
});
