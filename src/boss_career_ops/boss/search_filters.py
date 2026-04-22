from typing import Any


CITY_MAP = {
    "全国": "100010000",
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "杭州": "101210100",
    "成都": "101270100",
    "南京": "101190100",
    "武汉": "101200100",
    "西安": "101110100",
    "重庆": "101040100",
    "苏州": "101190400",
    "天津": "101030100",
    "长沙": "101250100",
    "郑州": "101180100",
    "东莞": "101281600",
    "沈阳": "101070100",
    "青岛": "101120200",
    "合肥": "101220100",
    "佛山": "101280800",
    "大连": "101070200",
    "宁波": "101210400",
    "昆明": "101290100",
    "厦门": "101230200",
    "珠海": "101280700",
    "无锡": "101190200",
    "福州": "101230100",
    "济南": "101120100",
    "哈尔滨": "101050100",
    "长春": "101060100",
    "南昌": "101240100",
    "贵阳": "101260100",
    "南宁": "101300100",
    "石家庄": "101090100",
    "太原": "101100100",
    "兰州": "101160100",
    "海口": "101310100",
    "常州": "101191100",
    "温州": "101210700",
    "嘉兴": "101210300",
    "徐州": "101190800",
    "香港": "101320100",
}

EXPERIENCE_MAP = {
    "在校/应届": "108",
    "1年以内": "101",
    "1-3年": "102",
    "3-5年": "103",
    "5-10年": "104",
    "10年以上": "105",
}

EDUCATION_MAP = {
    "初中及以下": "209",
    "中专/中技": "208",
    "高中": "206",
    "大专": "202",
    "本科": "203",
    "硕士": "204",
    "博士": "205",
}

JOB_TYPE_MAP = {
    "全职": "1901",
    "实习": "1902",
    "兼职": "1903",
}

SCALE_MAP = {
    "0-20人": "301",
    "20-99人": "302",
    "100-499人": "303",
    "500-999人": "304",
    "1000-9999人": "305",
    "10000人以上": "306",
}

FINANCE_MAP = {
    "未融资": "801",
    "天使轮": "802",
    "A轮": "803",
    "B轮": "804",
    "C轮": "805",
    "D轮及以上": "806",
    "已上市": "807",
    "不需要融资": "808",
}

SALARY_MAP = {
    "3K以下": "401",
    "3-5K": "402",
    "5-10K": "403",
    "10-15K": "404",
    "15-20K": "405",
    "20-30K": "406",
    "30-50K": "407",
    "50K以上": "408",
}


def get_city_code(city: str) -> str:
    return CITY_MAP.get(city, "")


def build_search_params(
    keyword: str,
    city: str = "",
    experience: str = "",
    education: str = "",
    job_type: str = "",
    scale: str = "",
    finance: str = "",
    salary: str = "",
    page: int = 1,
    page_size: int = 15,
) -> dict[str, Any]:
    params = {
        "query": keyword,
        "page": page,
        "pageSize": page_size,
    }
    city_code = get_city_code(city)
    if city_code:
        params["city"] = city_code
    if experience and experience in EXPERIENCE_MAP:
        params["experience"] = EXPERIENCE_MAP[experience]
    if education and education in EDUCATION_MAP:
        params["education"] = EDUCATION_MAP[education]
    if job_type and job_type in JOB_TYPE_MAP:
        params["jobType"] = JOB_TYPE_MAP[job_type]
    if scale and scale in SCALE_MAP:
        params["scale"] = SCALE_MAP[scale]
    if finance and finance in FINANCE_MAP:
        params["financeStage"] = FINANCE_MAP[finance]
    if salary and salary in SALARY_MAP:
        params["salary"] = SALARY_MAP[salary]
    return params


def filter_by_welfare(jobs: list[dict], welfare_keywords: str) -> list[dict]:
    if not welfare_keywords:
        return jobs
    keywords = [k.strip() for k in welfare_keywords.split(",") if k.strip()]
    if not keywords:
        return jobs
    result = []
    for job in jobs:
        job_welfares = job.get("jobLabels", []) or job.get("welfare", "").split("，")
        job_welfare_text = " ".join(job_welfares) if isinstance(job_welfares, list) else str(job_welfares)
        if all(kw in job_welfare_text for kw in keywords):
            result.append(job)
    return result
