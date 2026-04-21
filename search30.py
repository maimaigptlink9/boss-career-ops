"""Search Shenzhen agent jobs and output clean JSON."""
import subprocess, json, re, sys

result = subprocess.run(
    ["uv", "run", "bco", "search", "agent开发", "--city", "深圳", "--page", "1", "--limit", "30"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=r"d:\trae\boss-career-ops"
)
raw = result.stdout + result.stderr
raw = re.sub(r'\x1b\[[0-9;]*m', '', raw)
start = raw.find('{')
if start == -1:
    print("NO JSON FOUND")
    sys.exit(1)

decoder = json.JSONDecoder()
data, idx = decoder.raw_decode(raw, start)

if not data.get('ok'):
    print(f"SEARCH FAILED: {data.get('error')}")
    sys.exit(1)

jobs = data['data']
out = []
for j in jobs:
    out.append({
        'job': j.get('jobName', ''),
        'brand': j.get('brandName', ''),
        'salary': j.get('salaryDesc', ''),
        'exp': j.get('jobExperience', ''),
        'degree': j.get('jobDegree', ''),
        'area': j.get('areaDistrict', '') + j.get('businessDistrict', ''),
        'scale': j.get('brandScaleName', ''),
        'stage': j.get('brandStageName', ''),
        'industry': j.get('brandIndustry', ''),
        'skills': ','.join(j.get('skills', [])),
        'type': j.get('jobType', 0),
        'boss': j.get('bossTitle', ''),
    })

with open(r'd:\trae\boss-career-ops\output\jobs30.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Done: {len(out)} jobs saved to output/jobs30.json")
