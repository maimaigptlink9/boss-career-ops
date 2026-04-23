from boss_career_ops.display.output import output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_dashboard():
    try:
        from boss_career_ops.dashboard.app import BossCareerOpsApp
        app = BossCareerOpsApp()
        app.run()
    except Exception as e:
        output_error(command="dashboard", message=str(e), code="DASHBOARD_ERROR")
