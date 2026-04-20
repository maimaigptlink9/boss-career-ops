from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager

logger = get_logger(__name__)


def run_recommend():
    client = BossClient()
    settings = Settings()
    try:
        params = {}
        if settings.profile.preferred_cities:
            from boss_career_ops.boss.search_filters import get_city_code
            city = settings.profile.preferred_cities[0]
            city_code = get_city_code(city)
            if city_code:
                params["city"] = city_code
        if settings.profile.title:
            params["query"] = settings.profile.title
        resp = client.get("recommend", params=params)
        if resp.get("code") != 0:
            output_error(
                command="recommend",
                message=resp.get("message", "推荐失败"),
                code="RECOMMEND_ERROR",
                hints={"next_actions": ["bco status", "bco search"]},
            )
            return
        job_list = resp.get("zpData", {}).get("jobList", [])
        try:
            pm = PipelineManager()
            with pm:
                pm.batch_add_jobs(job_list)
            logger.info("已将 %d 条推荐结果写入 Pipeline", len(job_list))
        except Exception as e:
            logger.warning("推荐结果写入 Pipeline 失败: %s", e)
        output_json(
            command="recommend",
            data=job_list,
            hints={"next_actions": ["bco evaluate --from-search", "bco detail <security_id>"]},
        )
    except Exception as e:
        logger.error("推荐异常: %s", e)
        output_error(
            command="recommend",
            message=str(e),
            code="RECOMMEND_ERROR",
            hints={"next_actions": ["bco status", "bco login"]},
        )
