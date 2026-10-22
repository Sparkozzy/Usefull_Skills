import urllib.request
import json
import ssl

context = ssl._create_unverified_context()

url = "https://yctdkitkgqkdkznaqzrp.supabase.co/rest/v1/Prompts?select=id,Pormpt_Name"
req = urllib.request.Request(url)
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InljdGRraXRrZ3FrZGt6bmFxenJwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTAyMjE5NiwiZXhwIjoyMDk2NTk4MTk2fQ.0dPrM7Z5nVn5PJIXLWjaQqfw6PoGQHvzl5_KXVkSwmM"
req.add_header("apikey", key)
req.add_header("Authorization", f"Bearer {key}")

try:
    with urllib.request.urlopen(req, context=context) as response:
        data = json.loads(response.read().decode('utf-8'))
        print("Available prompts in ATS private database:")
        for row in data:
            id_val = row.get("id")
            name_val = str(row.get("Pormpt_Name")).encode("ascii", "replace").decode()
            print(f"ID: {id_val} | Name: {name_val}")
except Exception as e:
    print("Exception:", e)
