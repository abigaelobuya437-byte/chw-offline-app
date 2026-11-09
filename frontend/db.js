
const DB_NAME = "CHWDatabase";
const DB_VERSION = 1;
const STORE_NAME = "records";

function openDatabase() {
    return new Promise((resolve, reject) => {
        // Ask the browser to open our local database.
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        // Runs when the database is first created
        // or when its version changes.
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, {
                    keyPath: "local_id"
                });
            }
        };

        // Runs when the database opens successfully.
        request.onsuccess = (event) => {
            const db = event.target.result;
            resolve(db);
        };

        // Runs if the database cannot be opened.
        request.onerror = (event) => {
            reject(event.target.error);
        };
    });
}

async function saveRecord(record) {
    const db = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = db.transaction(
            "records",
            "readwrite"
        );

        const store = transaction.objectStore("records");

        const request = store.add(record);

        request.onsuccess = () => {
            resolve("Record saved successfully!");
        };

        request.onerror = () => {
            reject(request.error);
        };

        transaction.oncomplete = () => {
            db.close();
        };

        transaction.onerror = () => {
            db.close();
            reject(transaction.error);
        };

        transaction.onabort = () => {
            db.close();
            reject(transaction.error);
        };
    });
}


async function getAllRecords() {
    const db = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = db.transaction("records", "readonly");
        const store = transaction.objectStore("records");
        const request = store.getAll();

        request.onsuccess = () => {
            resolve(request.result);
        };

        request.onerror = () => {
            reject(request.error);
        };

        transaction.oncomplete = () => {
            db.close();
        };

        transaction.onerror = () => {
            db.close();
            reject(transaction.error);
        };

        transaction.onabort = () => {
            db.close();
            reject(transaction.error);
        };
    });
}

async function updateRecord(record) {
    const db = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = db.transaction("records", "readwrite");
        const store = transaction.objectStore("records");
        const request = store.put(record);

        request.onsuccess = () => {
            resolve("Record updated successfully!");
        };

        request.onerror = () => {
            reject(request.error);
        };

        transaction.oncomplete = () => {
            db.close();
        };

        transaction.onerror = () => {
            db.close();
            reject(transaction.error);
        };

        transaction.onabort = () => {
            db.close();
            reject(transaction.error);
        };
    });
}

