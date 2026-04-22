import json

d = json.load(open('output/search_agent_shenzhen.json', encoding='utf-8'))
data = d['data']
print(f"=== 搜索结果总数: {len(data)} ===\n")

print("--- 全部职位 ---")
for i, j in enumerate(data):
    print(f"{i+1}. {j['jobName']} | {j['brandName']} | {j['salaryDesc']} | {j['cityName']}{j.get('areaDistrict', '')} | {j['jobExperience']} | {j['jobDegree']} | 行业:{j.get('brandIndustry', '')} | 规模:{j.get('brandScaleName', '')}")

print("\n--- 跨境电商/电子商务行业 + 低门槛(经验<=3年) ---")
for i, j in enumerate(data):
    industry = j.get('brandIndustry', '')
    exp = j.get('jobExperience', '')
    is_ec = '电商' in industry or '电子商务' in industry or '贸易' in industry or '跨境' in industry or '物流' in industry
    is_low = '不限' in exp or '1-3' in exp or '在校' in exp
    if is_ec and is_low:
        print(f"  ★ {j['jobName']} | {j['brandName']} | {j['salaryDesc']} | {j['cityName']}{j.get('areaDistrict', '')} | {j['jobExperience']} | {j['jobDegree']} | 行业:{industry} | 规模:{j.get('brandScaleName', '')}")
        print(f"    securityId: {j['securityId'][:30]}... | encryptJobId: {j['encryptJobId']}")

print("\n--- 跨境电商/电子商务行业(不限经验要求) ---")
for i, j in enumerate(data):
    industry = j.get('brandIndustry', '')
    is_ec = '电商' in industry or '电子商务' in industry or '贸易' in industry or '跨境' in industry or '物流' in industry
    if is_ec:
        print(f"  {j['jobName']} | {j['brandName']} | {j['salaryDesc']} | {j['jobExperience']} | 行业:{industry}")
