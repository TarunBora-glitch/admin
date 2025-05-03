document.getElementById("studentRegisterForm").addEventListener("submit", function (e) {
  e.preventDefault();
  
  const formData = new FormData(this);

  fetch("/register-student", {
      method: "POST",
      body: formData
  })
  .then(response => response.text())
  .then(data => {
      if (data.includes("Invalid Credentials")) {  // ✅ If login fails, show error
          alert("Invalid register. Try again!");
      } else {
        alert("Registration Successfull!");
          window.location.href = "/";  // ✅ Redirect correctly
      }
  })
  .catch(error => console.error("Error:", error));
});

