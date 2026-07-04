import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Insert two rows with same source AND source_id
row1 = {
    'source': 'TEST-DUP',
    'source_id': 'dup-002',
    'name': 'Dup A',
    'description': 'test',
    'source_url': 'https://example.com',
    'url_is_live': True,
    'status': 'open',
}
row2 = {
    'source': 'TEST-DUP',
    'source_id': 'dup-002',
    'name': 'Dup B',
    'description': 'test',
    'source_url': 'https://example.com',
    'url_is_live': True,
    'status': 'open',
}

client.table('grants').insert(row1).execute()
try:
    client.table('grants').insert(row2).execute()
    print("ERROR: duplicate (source, source_id) was allowed")
except Exception as e:
    print(f"OK: duplicate blocked: {e}")

# Cleanup
client.table('grants').delete().eq('source_id', 'dup-002').execute()
print('Cleanup done')
