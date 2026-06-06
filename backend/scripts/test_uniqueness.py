import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Check constraints/indexes on grants table
resp = client.table('grants').select('source_id').limit(5).execute()
print('Sample source_ids:', [r['source_id'] for r in resp.data])

# Check if source_id alone is unique by trying to count duplicates
# We can do this via RPC or raw SQL
# Let's try a simple RPC call if available, otherwise just inspect schema via pg_catalog

try:
    # Try to see if we can query information_schema
    r = client.rpc('get_grants_constraints', {}).execute() if False else None
except:
    pass

# Simpler: try to insert two rows with same source_id but different source
row1 = {
    'source': 'TEST-A',
    'source_id': 'dup-test-001',
    'name': 'Dup Test A',
    'description': 'test',
    'source_url': 'https://example.com',
    'url_is_live': True,
    'status': 'open',
}
row2 = {
    'source': 'TEST-B',
    'source_id': 'dup-test-001',
    'name': 'Dup Test B',
    'description': 'test',
    'source_url': 'https://example.com',
    'url_is_live': True,
    'status': 'open',
}

# Insert both
client.table('grants').insert(row1).execute()
try:
    client.table('grants').insert(row2).execute()
    print("SUCCESS: same source_id with different source is ALLOWED (composite unique)")
except Exception as e:
    print(f"ERROR on second insert: {e}")
    print("This means source_id alone is unique")

# Cleanup
client.table('grants').delete().eq('source_id', 'dup-test-001').execute()
