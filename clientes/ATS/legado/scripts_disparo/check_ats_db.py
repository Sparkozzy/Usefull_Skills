import httpx

url = "https://yctdkitkgqkdkznaqzrp.supabase.co/rest/v1/Retell_calls_Mindflow"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InljdGRraXRrZ3FrZGt6bmFxenJwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTAyMjE5NiwiZXhwIjoyMDk2NTk4MTk2fQ.0dPrM7Z5nVn5PJIXLWjaQqfw6PoGQHvzl5_KXVkSwmM",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InljdGRraXRrZ3FrZGt6bmFxenJwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTAyMjE5NiwiZXhwIjoyMDk2NTk4MTk2fQ.0dPrM7Z5nVn5PJIXLWjaQqfw6PoGQHvzl5_KXVkSwmM"
}

params = {
    "order": "created_at.desc",
    "limit": 10
}

try:
    response = httpx.get(url, headers=headers, params=params, timeout=10.0)
    print("Status: ", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data)} recent calls in ATS DB:")
        for row in data:
            print(f"ID: {row.get('id')} | Created: {row.get('created_at')} | Name: {row.get('Nome')} | Number: {row.get('Numero')} | Status: {row.get('status')} | Reason: {row.get('disconnection_reason')} | Call ID: {row.get('call_id')}")
    else:
        print("Response:", response.text)
except Exception as e:
    print("Error:", e)
