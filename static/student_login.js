document.getElementById("studentLoginForm").addEventListener("submit", function (e) {
    e.preventDefault();
    
    const formData = new FormData(this);

    fetch("/student-login", {
        method: "POST",
        body: formData
    })
    .then(response => response.text())
    .then(data => {
        if (data.includes("Invalid Credentials") || data.includes("User not found")) {  // ✅ If login fails, show error
            alert("Invalid login. Try again!");
        } else {
            alert("Login successful");
            window.location.href = "/attendance";  // ✅ Redirect correctly
        }
    })
    .catch(error => console.error("Error:", error));
});
