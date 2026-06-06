import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Test upsert with composite on_conflict
row1 = {
    'source': 'TEST-COMP',
    'source_id': 'comp-001',
    'name': 'Composite Test',
    'description': 'test',
    'source_url': 'https://example.com',
    'url_is_live': True,
    'status': 'open',
    'eligibility_rules': {},
    'tags': ['test'],
    'metadata_json': {},
}

# Insert
resp = client.table('grants').insert(row1).execute()
print('Insert ok, id:', resp.data[0]['id'] if resp.data else 'N/A')

# Upsert same composite key, change name
row1['name'] = 'Composite Test Updated'
try:
    resp2 = client.table('grants').upsert(row1, on_conflict='source,source_id').execute()
    print('Upsert with source,source_id succeeded')
    print('Name after:', resp2.data[0]['name'] if resp2.data else 'N/A')
except Exception as e:
    print(f'Upsert failed: {e}')

# Cleanup
client.table('grants').delete().eq('source_id', 'comp-001').execute()
print('Cleanup done')
