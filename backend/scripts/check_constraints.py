import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Query information_schema to find unique constraints on grants
resp = client.rpc(
    'get_unique_constraints',
    {'table_name': 'grants'}
).execute()
print('Unique constraints:', resp.data)
