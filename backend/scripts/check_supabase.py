import sys
try:
    from supabase import Client
    print('supabase imported OK')
except Exception as e:
    print(f'import failed: {e}')
    sys.exit(1)
