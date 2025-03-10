async function getUserIdFromToken(token) {
    const payload = JSON.parse(atob(token.split(".")[1]));
    
    const currentTime = Math.floor(Date.now() / 1000);
    if (payload.exp < currentTime) {
        alert("Session expired. Please log in again.");
        sessionStorage.clear();
        window.location.href = "../index.html";
        return;
    }

    return payload.sub;
}

document.getElementById("loginForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    // To make sure requests only comes from frontend origin
    const allowedFrontend = "http://127.0.0.1:8000";
    if (window.location.origin !== allowedFrontend) {
        console.error("Unauthorized origin:", window.location.origin);
        document.getElementById("errorMessage").innerText = "Access denied!";
        return;
    }

    try {
        const response = await fetch("http://127.0.0.1:8000/login/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        console.log("Login Response:", data);
        if (response.ok) {
            sessionStorage.setItem("token", data.access_token);
            sessionStorage.setItem("role", data.role);
 
            if (data.role === "doctor") {
                window.location.href = "/frontend/dashboard/doctor.html";
            } else if (data.role === "patient") {
                window.location.href = "/frontend/dashboard/patient.html";
            } else {
                document.getElementById("errorMessage").innerText = "Invalid user role.";
            }
        } else {
            document.getElementById("errorMessage").innerText = data.detail || "Login failed!";
        }
    } catch (error) {
        document.getElementById("errorMessage").innerText = "Network error. Please try again later.";
    }
});
