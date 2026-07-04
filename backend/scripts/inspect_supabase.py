import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')

from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')

from supabase import create_client

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_KEY']
client = create_client(url, key)

# Try to fetch one grant to see actual column names
try:
    resp = client.table('grants').select('*').limit(1).execute()
    if resp.data:
        print("Existing grant columns:")
        for k, v in resp.data[0].items():
            print(f"  {k}: {type(v).__name__} = {repr(v)[:80]}")
    else:
        print("No grants in table. Trying to insert a minimal test row...")
        # Insert a minimal row with likely columns and see what error we get
        try:
            test = {
                'source_id': 'test-inspector-001',
                'name': 'Test Inspector',
                'description': 'Checking schema',
                'url': 'https://example.com',
                'provider_name': 'Test',
                'type': 'grant',
                'status': 'active',
            }
            resp2 = client.table('grants').insert(test).execute()
            print("Insert succeeded with columns: source_id, name, description, url, provider_name, type, status")
            # Clean up
            client.table('grants').delete().eq('source_id', 'test-inspector-001').execute()
        except Exception as e2:
            print(f"Insert error (reveals schema): {e2}")
except Exception as e:
    print(f"Fetch error: {e}")
