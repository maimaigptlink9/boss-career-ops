from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager

logger = get_logger(__name__)


def run_recommend():
    adapter = get_active_adapter()
    settings = Settings()
    try:
        params = {}
        if settings.profile.preferred_cities:
            city = settings.profile.preferred_cities[0]
            city_code = adapter.get_city_code(city)
            if city_code:
                params["city"] = city_code
        if settings.profile.title:
            params["query"] = settings.profile.title
        job_list = adapter.get_recommendations(params)
        if not job_list:
            output_error(
                command="recommend",
                message="推荐失败或无推荐结果",
                code="RECOMMEND_ERROR",
                hints={"next_actions": ["bco status", "bco search"]},
            )
            return
        try:
            pm = PipelineManager()
            with pm:
                pm.batch_add_jobs(job_list)
            logger.info("已将 %d 条推荐结果写入 Pipeline", len(job_list))
        except Exception as e:
            logger.warning("推荐结果写入 Pipeline 失败: %s", e)
        output_json(
            command="recommend",
            data=[j.to_dict() for j in job_list],
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
