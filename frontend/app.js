const networkStatus = document.getElementById("network-status");
const patientForm = document.getElementById("patient-form");
const message = document.getElementById("message");
const syncButton = document.getElementById("sync-button");

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showFeedback(text, type = "success") {
    if (!message) return;
    message.innerHTML = `
        <div class="alert alert-${type}">
            <span>${escapeHtml(text)}</span>
        </div>
    `;
}

function updateNetworkStatus() {
    const online = navigator.onLine;
    networkStatus.className = `status-badge ${online ? "status-online" : "status-offline"}`;
    networkStatus.innerHTML = `
        <span class="status-dot"></span>
        <span class="status-text">${online ? "ONLINE" : "OFFLINE"}</span>
    `;
}

window.addEventListener("online", updateNetworkStatus);
window.addEventListener("offline", updateNetworkStatus);

updateNetworkStatus();

patientForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    // Check that required form fields are valid.
    if (!patientForm.reportValidity()) {
        return;
    }

    // Collect the values entered in the form.
    const formData = new FormData(patientForm);
    const temperature = formData.get("vitals_temp");

    // Build a patient visit record.
    const record = {
        local_id: (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function")
            ? crypto.randomUUID()
            : "local_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9),
        chw_id: formData.get("chw_id").trim(),
        patient_name: formData.get("patient_name").trim(),
        village_name: formData.get("village_name").trim(),
        visit_type: formData.get("visit_type"),
        vitals_bp: formData.get("vitals_bp").trim(),
        vitals_temp: temperature === "" ? null : Number(temperature),
        urgency_level: formData.get("urgency_level"),
        visit_notes: formData.get("visit_notes").trim(),
        created_at_local: new Date().toISOString(),
        sync_status: "Pending"
    };

    try {
        // Save the record in the local browser database.
        await saveRecord(record);

        showFeedback("Patient record saved successfully on this device!", "success");

        // Clear the form after a successful save.
        patientForm.reset();

        // Refresh the saved records display and counter.
        await loadSavedRecords();

    } catch (error) {
        console.error("Could not save patient record:", error);
        showFeedback("Could not save the record. Please try again.", "error");
    }
});

// Startup check to verify database initialization
openDatabase()
    .then((db) => {
        console.log("Database connection successful!");
        console.log("Database name:", db.name);
        console.log("Stores:", Array.from(db.objectStoreNames));
        db.close();
    })
    .catch((error) => {
        console.error("Database connection failed:", error);
    });

async function loadSavedRecords() {
    const recordsList = document.getElementById("records-list");
    const countElement = document.getElementById("pending-count");

    try {
        const records = await getAllRecords();

        // Clear the old display before rebuilding it.
        recordsList.replaceChildren();

        // Count records waiting to sync.
        const pendingRecords = records.filter(
            record => record.sync_status === "Pending"
        );

        countElement.textContent = pendingRecords.length;

        if (records.length === 0) {
            recordsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <p class="empty-title">No records displayed yet</p>
                    <p class="empty-subtitle">New patient visit entries will appear in this queue.</p>
                </div>
            `;
            return;
        }

        // Display newest records first
        const sortedRecords = [...records].reverse();

        sortedRecords.forEach(record => {
            const card = document.createElement("article");
            const urgencyClass = (record.urgency_level || "routine").toLowerCase();
            const syncClass = (record.sync_status || "pending").toLowerCase();

            card.className = `record-card urgency-${urgencyClass}`;

            const formattedDate = record.created_at_local
                ? new Date(record.created_at_local).toLocaleString([], {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit"
                })
                : "Just now";

            card.innerHTML = `
                <div class="record-card-top">
                    <div class="record-patient">
                        <h3 class="record-name">${escapeHtml(record.patient_name)}</h3>
                        <span class="record-village">📍 ${escapeHtml(record.village_name)}</span>
                    </div>
                    <div class="record-badges">
                        <span class="badge badge-${urgencyClass}">${escapeHtml(record.urgency_level || "Routine")}</span>
                        <span class="badge badge-sync-${syncClass}">${escapeHtml(record.sync_status || "Pending")}</span>
                    </div>
                </div>

                <div class="record-chips">
                    <span class="record-chip">Type: <strong>${escapeHtml(record.visit_type || "General")}</strong></span>
                    ${record.vitals_bp ? `<span class="record-chip">BP: <strong>${escapeHtml(record.vitals_bp)}</strong></span>` : ''}
                    ${record.vitals_temp !== null && record.vitals_temp !== undefined ? `<span class="record-chip">Temp: <strong>${escapeHtml(String(record.vitals_temp))}°C</strong></span>` : ''}
                    <span class="record-chip">CHW: <strong>${escapeHtml(record.chw_id || "N/A")}</strong></span>
                </div>

                ${record.visit_notes ? `<p class="record-notes">${escapeHtml(record.visit_notes)}</p>` : ''}

                <div class="record-footer">
                    <span>Recorded</span>
                    <time>${formattedDate}</time>
                </div>
            `;

            recordsList.appendChild(card);
        });

    } catch (error) {
        console.error("Could not load saved records:", error);
        recordsList.innerHTML = `<div class="alert alert-error">Could not load saved records.</div>`;
    }
}

// Load records whenever the page opens.
loadSavedRecords();

// Wire up the sync button
if (syncButton) {
    syncButton.addEventListener("click", async () => {
        if (!navigator.onLine) {
            showFeedback("Cannot sync while offline. Please connect to the internet.", "error");
            return;
        }

        try {
            const records = await getAllRecords();
            const pendingRecords = records.filter(
                record => record.sync_status === "Pending"
            );

            if (pendingRecords.length === 0) {
                showFeedback("No pending records to sync.", "info");
                return;
            }

            syncButton.disabled = true;
            syncButton.textContent = `Syncing (${pendingRecords.length})...`;
            showFeedback(`Syncing ${pendingRecords.length} record(s)...`, "info");

            let syncedCount = 0;
            for (const record of pendingRecords) {
                try {
                    const response = await fetch("/api/records", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(record)
                    });

                    if (response.ok) {
                        record.sync_status = "Synced";
                        await updateRecord(record);
                        syncedCount++;
                    }
                } catch (err) {
                    console.warn(`Failed to sync record ${record.local_id}:`, err);
                }
            }

            await loadSavedRecords();

            if (syncedCount > 0) {
                showFeedback(`Successfully synced ${syncedCount} record(s).`, "success");
            } else {
                showFeedback("Sync failed: server is unreachable or endpoint returned an error.", "error");
            }
        } catch (error) {
            console.error("Sync error:", error);
            showFeedback("Could not complete synchronization.", "error");
        } finally {
            syncButton.disabled = false;
            syncButton.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
                </svg>
                Sync Queue
            `;
        }
    });
}
