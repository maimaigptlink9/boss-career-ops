import httpx
import yaml

from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

SKILL_RAW_URL = "https://raw.githubusercontent.com/maimaigptlink9/boss-career-ops/main/skills/boss-career-ops/skill.md"


def _parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _fetch_remote_skill() -> str | None:
    try:
        resp = httpx.get(SKILL_RAW_URL, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError as e:
        logger.warning("获取远程 skill.md 失败: %s", e)
        return None


def run_skill_update(check_only: bool = False):
    remote_content = _fetch_remote_skill()
    if remote_content is None:
        output_error(
            command="skill-update",
            message="无法获取远程 skill.md，请检查网络连接",
            code="NETWORK_ERROR",
            hints={"next_actions": ["检查网络后重试"]},
        )
        return

    remote_fm = _parse_frontmatter(remote_content)
    remote_version = str(remote_fm.get("skill_version", "0.0.0"))

    if check_only:
        output_json(
            command="skill-update",
            data={
                "remote_version": remote_version,
                "content": None,
            },
            hints={"next_actions": ["若需要更新，执行 bco skill-update"]},
        )
        return

    output_json(
        command="skill-update",
        data={
            "remote_version": remote_version,
            "content": remote_content,
        },
        hints={"next_actions": ["将 content 写入 skill.md 即完成更新"]},
    )
