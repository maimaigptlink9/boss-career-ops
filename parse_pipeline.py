import json, re, sys

raw = sys.stdin.buffer.read().decode('utf-8', errors='replace')
raw = re.sub(r'\x1b\[[0-9;]*m', '', raw)
start = raw.find('{')
if start == -1:
    print('NO JSON')
    sys.exit(1)

decoder = json.JSONDecoder()
data, idx = decoder.raw_decode(raw, start)
jobs = data['data']
print(f'Total pipeline jobs: {len(jobs)}')

out = []
for j in jobs:
    out.append({
        'job': j['job_name'],
        'brand': j['company_name'],
        'salary': j['salary_desc'],
        'stage': j['stage'],
        'score': j['score'],
        'grade': j['grade'],
    })

with open('output/pipeline_clean.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# just save to file, no print to avoid encoding issues
print(f"Saved {len(out)} jobs to output/pipeline_clean.json")
