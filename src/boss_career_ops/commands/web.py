import webbrowser

from boss_career_ops.display.output import output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_web(host="127.0.0.1", port=8080, no_browser=False):
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print("错误：Web 功能需要安装额外依赖。请运行：uv add fastapi uvicorn")
        return
    try:
        if not no_browser:
            url = f"http://{host}:{port}"
            webbrowser.open(url)
        uvicorn.run(
            "boss_career_ops.web.server:app",
            host=host,
            port=port,
            reload=False,
        )
    except Exception as e:
        output_error(command="web", message=str(e), code="WEB_ERROR")
