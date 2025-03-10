document.addEventListener("DOMContentLoaded", async function() {
    const token = sessionStorage.getItem("token");
    const role = sessionStorage.getItem("role");

    if (!token || role !== "doctor") {
        alert("Unauthorized access. Redirecting to login...");
        window.location.href = "../index.html";
        return;
    }

    document.getElementById("searchPatientBtn").addEventListener("click", async function() {
        const patientId = document.getElementById("patientIdInput").value.trim();
        if (!patientId) {
            document.getElementById("searchError").innerText = "Please enter a Patient ID.";
            return;
        }
        await fetchMedicalRecords(patientId, token);
    });

    document.getElementById("logoutBtn").addEventListener("click", function() {
        sessionStorage.clear();
        window.location.href = "../index.html";
    });

    document.getElementById("confirmUpdateBtn").addEventListener("click", async function() {
        const updatedDetails = document.getElementById("updatedDetails").value.trim();
        if (!updatedDetails) {
            alert("Updated details are required.");
            return;
        }

        const recordId = sessionStorage.getItem("selectedRecordId");
        if (!recordId) {
            alert("No record selected.");
            return;
        }

        await updateMedicalRecord(recordId, updatedDetails, token);
    });

    document.getElementById("cancelUpdateBtn").addEventListener("click", function() {
        document.getElementById("updateForm").style.display = "none";
    });
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
            if (record.doctor_id == sessionStorage.getItem("userId")) {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${record.id}</td>
                    <td>${record.record_details}</td>
                    <td>${new Date(record.timestamp).toLocaleString()}</td>
                    <td><button onclick="selectRecord(${record.id})">Select</button></td>
                `;
                tableBody.appendChild(row);
            }
        });

    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan='4' class="error-text">${error.message}</td></tr>`;
    }
}

function selectRecord(recordId) {
    sessionStorage.setItem("selectedRecordId", recordId);
    document.getElementById("updateForm").style.display = "block";
}

async function updateMedicalRecord(recordId, updatedDetails, token) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/records/update/${recordId}`, {
            method: "PUT",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ record_details: updatedDetails })
        });

        if (!response.ok) throw new Error("Failed to update record.");

        alert("Medical record updated successfully.");
        document.getElementById("updateForm").style.display = "none";
        document.getElementById("updatedDetails").value = "";
        const patientId = document.getElementById("patientIdInput").value.trim();
        await fetchMedicalRecords(patientId, token);
    } catch (error) {
        alert(error.message);
    }
}
