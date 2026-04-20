import shutil
from pathlib import Path

import yaml

from boss_career_ops.config.settings import BCO_HOME, CONFIG_DIR, CV_PATH, EXPORTS_DIR, RESUMES_DIR, WATCHES_DIR
from boss_career_ops.display.output import output_json, output_error

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

PROFILE_TEMPLATE = {
    "name": "",
    "title": "",
    "experience_years": 0,
    "skills": [],
    "expected_salary": {"min": 0, "max": 0},
    "preferred_cities": [],
    "remote_ok": False,
    "education": "",
    "career_goals": "",
    "avoid": "",
}

THRESHOLDS_TEMPLATE = {
    "auto_action": {
        "auto_greet_threshold": 4.0,
        "auto_apply_threshold": 4.5,
        "skip_threshold": 2.0,
        "confirm_required": True,
    },
    "rate_limit": {
        "request_delay_min": 1.5,
        "request_delay_max": 3.0,
        "batch_greet_max": 10,
        "batch_greet_delay_min": 2.0,
        "batch_greet_delay_max": 5.0,
        "burst_penalty_multiplier": 2.0,
        "retry_max_attempts": 3,
        "retry_base_delay": 5.0,
        "retry_max_delay": 60.0,
        "search_page_delay_min": 3.0,
        "search_page_delay_max": 6.0,
        "search_max_pages": 5,
    },
    "cache": {
        "default_ttl": 3600,
        "search_ttl": 1800,
    },
}


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return True
    return False


def _write_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def run_setup():
    steps = []

    BCO_HOME.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    profile_path = CONFIG_DIR / "profile.yml"
    thresholds_path = CONFIG_DIR / "thresholds.yml"
    cv_path = CV_PATH

    if profile_path.exists():
        steps.append({"step": "profile.yml", "status": "已存在，跳过", "path": str(profile_path)})
    else:
        example = _DATA_DIR / "profile.example.yml"
        if _copy_if_exists(example, profile_path):
            steps.append({"step": "profile.yml", "status": "已从模板创建", "path": str(profile_path)})
        else:
            _write_yaml(profile_path, PROFILE_TEMPLATE)
            steps.append({"step": "profile.yml", "status": "已创建默认配置", "path": str(profile_path)})

    if thresholds_path.exists():
        steps.append({"step": "thresholds.yml", "status": "已存在，跳过", "path": str(thresholds_path)})
    else:
        example = _DATA_DIR / "thresholds.example.yml"
        if _copy_if_exists(example, thresholds_path):
            steps.append({"step": "thresholds.yml", "status": "已从模板创建", "path": str(thresholds_path)})
        else:
            _write_yaml(thresholds_path, THRESHOLDS_TEMPLATE)
            steps.append({"step": "thresholds.yml", "status": "已创建默认配置", "path": str(thresholds_path)})

    if cv_path.exists():
        steps.append({"step": "cv.md", "status": "已存在，跳过", "path": str(cv_path)})
    else:
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(
            "# 个人简历\n\n"
            "请在此处填写您的完整简历。评估引擎和简历生成器都会读取此文件。\n\n"
            "越详细，评估越准确。\n\n"
            "## 基本信息\n\n"
            "- 姓名：\n- 职位：\n- 工作年限：\n- 学历：\n\n"
            "## 技能\n\n-\n\n"
            "## 工作经历\n\n"
            "### 公司名称 | 职位 | 时间段\n\n-\n\n"
            "## 项目经历\n\n"
            "### 项目名称 | 时间段\n\n-\n\n"
            "## 教育背景\n\n"
            "### 学校 | 专业 | 学历 | 时间段\n",
            encoding="utf-8",
        )
        steps.append({"step": "cv.md", "status": "已创建模板", "path": str(cv_path)})

    for dir_label, dir_path in [
        ("exports", EXPORTS_DIR),
        ("resumes", RESUMES_DIR),
        ("watches", WATCHES_DIR),
    ]:
        if dir_path.exists():
            steps.append({"step": f"{dir_label}/", "status": "已存在，跳过", "path": str(dir_path)})
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            steps.append({"step": f"{dir_label}/", "status": "已创建", "path": str(dir_path)})

    output_json(
        command="setup",
        data={
            "bco_home": str(BCO_HOME),
            "steps": steps,
        },
        hints={
            "next_actions": [
                f"编辑个人信息: {profile_path}",
                f"编辑简历: {cv_path}",
                "运行 bco login 登录 BOSS 直聘",
                "运行 bco ai-config 配置 AI（可选）",
            ]
        },
    )
