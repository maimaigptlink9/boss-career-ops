from typing import Any


CITY_MAP = {
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
}

EXPERIENCE_MAP = {
    "应届": "101",
    "1年以内": "102",
    "1-3年": "103",
    "3-5年": "104",
    "5-10年": "105",
    "10年以上": "106",
}

EDUCATION_MAP = {
    "初中及以下": "201",
    "中专/中技": "202",
    "高中": "203",
    "大专": "204",
    "本科": "205",
    "硕士": "206",
    "博士": "207",
}

JOB_TYPE_MAP = {
    "全职": "301",
    "兼职": "302",
    "实习": "303",
}

SCALE_MAP = {
    "0-20人": "401",
    "20-99人": "402",
    "100-499人": "403",
    "500-999人": "404",
    "1000-9999人": "405",
    "10000人以上": "406",
}

FINANCE_MAP = {
    "未融资": "501",
    "天使轮": "502",
    "A轮": "503",
    "B轮": "504",
    "C轮": "505",
    "D轮及以上": "506",
    "已上市": "507",
    "不需要融资": "508",
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
