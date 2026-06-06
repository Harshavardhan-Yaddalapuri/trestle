import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Test status constraint by trying to insert invalid status
row = {
    'source': 'TEST-STATUS',
    'source_id': 'status-test-001',
    'name': 'Status Test',
    'description': 'test',
    'source_url': 'https://example.com',
    'url_is_live': True,
    'status': 'active',
}
try:
    client.table('grants').insert(row).execute()
    print("status='active' is ALLOWED")
    client.table('grants').delete().eq('source_id', 'status-test-001').execute()
except Exception as e:
    print(f"status='active' FAILED: {e}")

row['status'] = 'open'
try:
    client.table('grants').insert(row).execute()
    print("status='open' is ALLOWED")
    client.table('grants').delete().eq('source_id', 'status-test-001').execute()
except Exception as e:
    print(f"status='open' FAILED: {e}")
