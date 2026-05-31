import json
with open('data/processed/e1_e3_analysis_results.json','r') as f:
    r = json.load(f)
print('e3_bootstrap keys:', list(r['e3_bootstrap'].keys()))
print('e3_bootstrap n=3:', r['e3_bootstrap']['3'] if '3' in r['e3_bootstrap'] else 'MISSING')
print('e3_fss:', r.get('e3_fss'))