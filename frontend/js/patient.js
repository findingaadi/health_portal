document.addEventListener("DOMContentLoaded", async function () {
    const token = sessionStorage.getItem("token");
    const role = sessionStorage.getItem("role");

    if (!token || role !== "patient") {
        alert("Unauthorized access. Redirecting to login...");
        window.location.href = "../index.html";
        return;
    }

    const patientId = await getUserIdFromToken(token);
    document.getElementById("welcomeMessage").innerText = `Welcome ${sessionStorage.getItem("username")}, your Patient ID is: ${patientId}`;

    await fetchMedicalRecords(patientId, token);
    await fetchMedicalLogs(patientId, token);
});

async function getUserIdFromToken(token) {
    const payload = JSON.parse(atob(token.split(".")[1]));

    if (payload.exp < Math.floor(Date.now() / 1000)) {
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
        recordsContainer.innerHTML = records.length
            ? records.map(record => `
                <tr>
                    <td>${record.id}</td>
                    <td>${record.doctor_id}</td>
                    <td>${record.record_details}</td>
                    <td>${new Date(record.timestamp).toLocaleString()}</td>
                </tr>`).join("")
            : "<tr><td colspan='4' class='no-data'>No medical records found.</td></tr>";

    } catch (error) {
        recordsContainer.innerHTML = `<tr><td colspan="4" class="error-text">${error.message}</td></tr>`;
    }
}
async function fetchMedicalLogs(patientId, token) {
    const logsContainer = document.getElementById("medicalLogs");

    try {
        const response = await fetch(`http://127.0.0.1:8000/immdb/log/${patientId}`, {
            method: "GET",
            headers: {"Authorization": `Bearer ${token}`,"Content-Type": "application/json"}
        });

        if (!response.ok) throw new Error("Failed to fetch medical logs.");

        const logs = await response.json();
        logsContainer.innerHTML = "";

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
    sessionStorage.clear();
    window.location.href = "../index.html";
});