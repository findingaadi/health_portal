document.addEventListener("DOMContentLoaded", async function() {
    const token = sessionStorage.getItem("token");
    const role = sessionStorage.getItem("role");

    if (!token || role !== "doctor") {
        alert("Unauthorized access. Redirecting to login...");
        window.location.href = "../index.html";
        return;
    }
    const patientId = await getUserIdFromToken(token);
    document.getElementById("welcomeMessage").innerText = `Welcome Dr. ${sessionStorage.getItem("username")}`;

    document.getElementById("searchPatientBtn").addEventListener("click", async function() {
        const patientId = document.getElementById("patientIdInput").value.trim();
        if (!patientId) {
            document.getElementById("searchError").innerText = "Please enter a Patient ID.";
            return;
        }
        await fetchMedicalRecords(patientId, token);
    });

    document.getElementById("showAddRecordForm").addEventListener("click", function() {
        document.getElementById("addRecordForm").style.display = "block";
    });

    document.getElementById("cancelAddRecord").addEventListener("click", function() {
        document.getElementById("addRecordForm").style.display = "none";
    });

    document.getElementById("confirmAddRecord").addEventListener("click", async function() {
        const patientId = document.getElementById("patientIdInput").value.trim();
        const recordDetails = document.getElementById("recordDetails").value.trim();

        if (!patientId || !recordDetails) {
            alert("Patient ID and record details are required.");
            return;
        }

        await addMedicalRecord(patientId, recordDetails, token);
    });


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


document.getElementById("logoutBtn").addEventListener("click", function() {
    sessionStorage.clear();
    window.location.href = "../index.html";
});

async function fetchMedicalRecords(patientId, token) {
    const tableBody = document.querySelector("#medicalRecordsTable tbody");
    tableBody.innerHTML = "<tr><td colspan='4'>Loading records...</td></tr>";

    try {
        const response = await fetch(`http://127.0.0.1:8000/records/patient/${patientId}`, {
            method: "GET",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("No records found for this patient.");

        const records = await response.json();
        tableBody.innerHTML = "";

        records.forEach(record => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${record.id}</td>
                <td>${record.record_details}</td>
                <td>${record.doctor_id}</td>
                <td>${new Date(record.timestamp).toLocaleString()}</td>
            `;
            tableBody.appendChild(row);
        });

    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan='4' class="error-text">${error.message}</td></tr>`;
    }
}

async function addMedicalRecord(patientId, recordDetails, token) {
    try {
        const response = await fetch("http://127.0.0.1:8000/records/", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ patient_id: parseInt(patientId), record_details: recordDetails })
        });

        if (!response.ok) throw new Error("Failed to add record.");

        alert("Medical record added successfully.");
        document.getElementById("recordDetails").value = "";
        document.getElementById("addRecordForm").style.display = "none";
        await fetchMedicalRecords(patientId, token);
    } catch (error) {
        alert(error.message);
    }
}
