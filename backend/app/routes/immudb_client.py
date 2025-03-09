import time
from datetime import datetime
from immudb.client import ImmudbClient
from app.config import IMMUDDB_HOST, IMMUDDB_PORT, IMMUDDB_USER, IMMUDDB_PASSWORD

def get_immudb_client(retries=3, delay=2):
    for attempt in range(retries):
        try:
            client = ImmudbClient(f"{IMMUDDB_HOST}:{IMMUDDB_PORT}")
            client.login(IMMUDDB_USER, IMMUDDB_PASSWORD)
            print("immudb logged in")
            return client
        except Exception as e:
            print(f"Attempt {attempt + 1}: immudb login failed. Retrying.")
            time.sleep(delay)
    raise RuntimeError("Failed to connect to immudb after multiple attempts")

# Initialize the immudb client so it can be imported elsewhere
immu_client = get_immudb_client()

def log_access(patient_id: int, doctor_id: int, action: str):
    try:
        log_entry = f"Doctor {doctor_id} {action} medical record of Patient {patient_id} at {datetime.now()}."
        immu_client.set(str(patient_id).encode("utf-8"), log_entry.encode("utf-8"))
    except Exception as e:
        print(f"Failed to log access in immudb: {e}")