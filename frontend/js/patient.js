document.addEventListener("DOMContentLoaded", async function() {
    const token = sessionStorage.getItem("token");
    const role = sessionStorage.getItem("role");

    if (!token || role !== "patient") {
        alert("Unauthorized access. Redirecting to login...");
        window.location.href = "../index.html";
        return;
    }
    
    const patientId = await getUserIdFromToken(token);
    document.getElementById("welcomeMessage").innerText = `Welcome ${sessionStorage.getItem("username")} your Patient ID is: ${sessionStorage.getItem("userId")}`;

    await fetchMedicalRecords(patientId, token);
    await fetchMedicalLogs(patientId, token);
});

async function getUserIdFromToken(token) {
    const payload = JSON.parse(atob(token.split(".")[1]));
    
    const currentTime = Math.floor(Date.now() / 1000);
    if (payload.exp < currentTime) {
        alert("Session expired. Please log in again.");
        sessionStorage.clear();
        window.location.href = "../index.html";
        return;
    }

    sessionStorage.setItem("userId", payload.sub);
    sessionStorage.setItem("username", payload.name);
    return payload.sub;
}

async function fetchMedicalRecords(patientId, token) {
    const recordsContainer = document.getElementById("medicalRecords");
    try {
        const response = await fetch(`http://127.0.0.1:8000/records/patient/${patientId}`, {
            method: "GET",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Failed to fetch medical records.");

        const records = await response.json();
        recordsContainer.innerHTML = "";

        if (records.length === 0) {
            recordsContainer.innerHTML = "<p>No medical records found.</p>";
            return;
        }

        records.forEach(record => {
            const recordDiv = document.createElement("div");
            recordDiv.classList.add("record-item");
            recordDiv.innerHTML = `
                <p><strong>ID:</strong> ${record.id}</p>
                <p><strong>Doctor ID:</strong> ${record.doctor_id}</p>
                <p><strong>Details:</strong> ${record.record_details}</p>
                <p><strong>Timestamp:</strong> ${new Date(record.timestamp).toLocaleString()}</p>
            `;
            recordsContainer.appendChild(recordDiv);
        });
    } catch (error) {
        recordsContainer.innerHTML = `<p class="error-text">${error.message}</p>`;
    }
}

async function fetchMedicalLogs(patientId, token) {
    const logsContainer = document.getElementById("medicalLogs");

    try {
        const response = await fetch(`http://127.0.0.1:8000/immdb/log/${patientId}`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (response.status === 403) {
            logsContainer.innerHTML = `<p class="error-text">Access Denied: You can only view your own logs.</p>`;
            return;
        }

        if (!response.ok) throw new Error("Failed to fetch medical logs.");

        const logs = await response.json();
        logsContainer.innerHTML = "";

        if (logs.length === 0) {
            logsContainer.innerHTML = "<p>No logs found.</p>";
            return;
        }

        logs.forEach(log => {
            const logDiv = document.createElement("div");
            logDiv.classList.add("log-item");
            logDiv.innerHTML = `<p>${log.log}</p>`;
            logsContainer.appendChild(logDiv);
        });

    } catch (error) {
        logsContainer.innerHTML = `<p class="error-text">${error.message}</p>`;
    }
}

document.getElementById("logoutBtn").addEventListener("click", function() {
    localStorage.clear();
    window.location.href = "../index.html";
});