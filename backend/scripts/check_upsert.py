import os, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')
from dotenv import load_dotenv
load_dotenv('/Users/harshavardhan/trestle/.env')
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
# Print methods of the query builder
methods = [m for m in dir(client.table('grants')) if not m.startswith('_')]
print([m for m in methods if 'upsert' in m.lower() or 'insert' in m.lower()])
