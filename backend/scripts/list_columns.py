import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

resp = client.table('grants').select('*').limit(1).execute()
if resp.data:
    for k in sorted(resp.data[0].keys()):
        print(f"  {k}")
else:
    print('No data')
