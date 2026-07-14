cd /home/jonah/Projects/trestle

REF=$(python - <<'PY'
from urllib.parse import urlparse
import os
u=os.environ.get("SUPABASE_URL","")
print(urlparse(u).netloc.replace(".supabase.co",""))
PY
)

for r in us-east-1 us-west-1 us-west-2 eu-west-1 eu-central-1 ap-southeast-1 ap-northeast-1; do
  echo "== testing $r =="
  docker run --rm -e PGPASSWORD="$SUPABASE_DB_PASSWORD" postgres:16-alpine \
    psql "host=aws-0-$r.pooler.supabase.com port=5432 user=postgres.$REF dbname=postgres sslmode=require connect_timeout=5" \
    -c "select 1;" 2>&1 | rg -i "select 1|password authentication failed|tenant/user|could not translate host|timeout|no route|refused"
  echo
done
