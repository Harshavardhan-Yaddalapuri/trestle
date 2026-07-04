import asyncio, sys
sys.path.insert(0, '/Users/harshavardhan/trestle')

from backend.ingestion.fetchers.grants_gov import GrantsGovFetcher
from backend.ingestion.fetchers.nsf import NSFFetcher
from backend.ingestion.fetchers.sbir_gov import SBIRGovFetcher
from backend.ingestion.normalizer import normalize_batch

async def dry_run():
    print('Fetching Grants.gov (SBIR keyword)...')
    async with GrantsGovFetcher() as f:
        gg = await f.fetch_all(keyword='SBIR', rows=25, max_pages=1)
    print(f'  Grants.gov raw count: {len(gg)}')
    if gg:
        print(f'  Sample keys: {list(gg[0].keys())[:15]}')
        print(f'  Sample title: {gg[0].get("title", "N/A")}')

    print('\nFetching NSF via Grants.gov proxy...')
    async with NSFFetcher() as f:
        nsf = await f.fetch_all(rows=25, max_pages=1)
    print(f'  NSF raw count: {len(nsf)}')
    if nsf:
        print(f'  Sample keys: {list(nsf[0].keys())[:15]}')
        print(f'  Sample title: {nsf[0].get("title", "N/A")}')

    print('\nFetching SBIR.gov...')
    async with SBIRGovFetcher() as f:
        sbir = await f.fetch_all(rows=25, max_pages=1)
    print(f'  SBIR.gov raw count: {len(sbir)}')
    if sbir:
        print(f'  Sample keys: {list(sbir[0].keys())[:15]}')
        print(f'  Sample title: {sbir[0].get("title", "N/A")}')

    all_raw = gg + nsf + sbir
    print(f'\nTotal raw records: {len(all_raw)}')

    print('\nNormalizing...')
    normalized = normalize_batch(all_raw)
    print(f'  Normalized count: {len(normalized)}')
    if normalized:
        print(f'  Sample normalized keys: {list(normalized[0].keys())}')
        print(f'  Sample name: {normalized[0].get("name", "N/A")}')
        print(f'  Sample source: {normalized[0].get("source", "N/A")}')
        print(f'  Sample source_id: {normalized[0].get("source_id", "N/A")}')

    return all_raw, normalized

if __name__ == '__main__':
    raw, norm = asyncio.run(dry_run())
