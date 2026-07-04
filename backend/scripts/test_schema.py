import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Insert with only known-good fields
row = {
    'source': 'TEST-CHECK',
    'source_id': 'test-schema-check-001',
    'name': 'Schema Check',
    'description': 'Checking exact schema',
    'amount_min_usd': None,
    'amount_max_usd': None,
    'deadline': None,
    'status': 'open',
    'eligibility_rules': {},
    'tags': ['test'],
    'source_url': 'https://example.com',
    'url_is_live': True,
    'metadata_json': {'test': True},
    'last_synced_at': None,
}

try:
    resp = client.table('grants').insert(row).execute()
    print('Insert succeeded with known-good fields')
    print('Returned id:', resp.data[0]['id'])
    client.table('grants').delete().eq('source_id', 'test-schema-check-001').execute()
    print('Cleanup done')
except Exception as e:
    print(f'Insert failed: {e}')
