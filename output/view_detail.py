import json

d = json.load(open('output/search_agent_shenzhen.json', encoding='utf-8'))
data = d['data']

targets = {
    '通达致远': None,
    '九方通逊': None,
    '蔚库': None,
}

for j in data:
    brand = j.get('brandName', '')
    for key in targets:
        if key in brand and targets[key] is None:
            targets[key] = j

for key, j in targets.items():
    if j:
        print(f"\n{'='*60}")
        print(f"公司: {j['brandName']}")
        print(f"职位: {j['jobName']}")
        print(f"薪资: {j['salaryDesc']}")
        print(f"经验: {j['jobExperience']}")
        print(f"学历: {j['jobDegree']}")
        print(f"地点: {j['cityName']}{j.get('areaDistrict', '')} {j.get('businessDistrict', '')}")
        print(f"行业: {j.get('brandIndustry', '')}")
        print(f"规模: {j.get('brandScaleName', '')}")
        print(f"融资: {j.get('brandStageName', '')}")
        print(f"技能标签: {j.get('skills', [])}")
        print(f"福利: {j.get('welfareList', [])}")
        print(f"securityId: {j['securityId']}")
        print(f"encryptJobId: {j['encryptJobId']}")
        print(f"encryptBossId: {j['encryptBossId']}")
        print(f"BOSS: {j.get('bossName', '')} ({j.get('bossTitle', '')})")
    else:
        print(f"\n{'='*60}")
        print(f"未找到: {key}")
