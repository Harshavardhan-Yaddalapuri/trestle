import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Try upsert on source_id
row = {
    'source': 'TEST-PIPELINE',
    'source_id': 'test-upsert-001',
    'name': 'Test Upsert',
    'description': 'A test row for upsert validation',
    'source_url': 'https://example.com',
    'url_is_live': True,
    'status': 'open',
    'type': 'grant',
    'provider_name': 'Test Agency',
    'provider_type': 'government',
    'eligibility_rules': {'test': True},
    'tags': ['test'],
    'metadata_json': {'via': 'pipeline test'},
}

# First insert
resp1 = client.table('grants').upsert(row, on_conflict='source_id').execute()
print('First upsert (insert):', len(resp1.data), 'rows')

# Modify and upsert again
row['name'] = 'Test Upsert Updated'
resp2 = client.table('grants').upsert(row, on_conflict='source_id').execute()
print('Second upsert (update):', len(resp2.data), 'rows')
print('Name after upsert:', resp2.data[0]['name'])

# Cleanup
client.table('grants').delete().eq('source_id', 'test-upsert-001').execute()
print('Cleanup done')
