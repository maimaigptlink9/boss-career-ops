from unittest.mock import patch, MagicMock

from boss_career_ops.resume.generator import ResumeGenerator
from boss_career_ops.resume.keywords import KeywordInjector, ATS_KEYWORD_CATEGORIES
from boss_career_ops.resume.pdf_engine import PDFEngine
from boss_career_ops.config.settings import Settings, Profile


class TestResumeGenerator:
    def _make_generator(self, cv_content="", profile=None):
        with patch.object(Settings, '__init__', lambda self, *a, **kw: None):
            settings = Settings()
            settings.profile = profile or Profile()
            settings.cv_content = cv_content
            gen = ResumeGenerator()
            gen._settings = settings
            return gen

    def test_generate_from_profile(self):
        profile = Profile(name="张三", title="工程师", skills=["Go", "Docker"], education="本科")
        gen = self._make_generator(profile=profile)
        result = gen.generate({"jobName": "Golang"})
        assert "张三" in result
        assert "Go" in result

    def test_generate_from_cv(self):
        cv = "# 简历\n\n## 技能\n- Python\n- Go"
        gen = self._make_generator(cv_content=cv)
        result = gen.generate({"jobName": "Golang", "brandName": "公司", "skills": "Go,Kubernetes"})
        assert "定制" in result

    def test_extract_skills_from_jd(self):
        gen = self._make_generator()
        jd = "需要 Python, Docker, Kubernetes 经验"
        skills = gen._extract_skills_from_jd(jd)
        assert "Python" in skills
        assert "Docker" in skills

    def test_extract_skills_from_jd_no_match(self):
        gen = self._make_generator()
        skills = gen._extract_skills_from_jd("需要一些其他技能")
        assert skills == []


class TestKeywordInjector:
    def test_extract_from_jd(self):
        injector = KeywordInjector()
        jd = "需要 Python 和 Docker 经验，熟悉 Agile 开发"
        keywords = injector.extract_from_jd(jd)
        assert "Python" in keywords
        assert "Docker" in keywords
        assert "Agile" in keywords

    def test_extract_no_match(self):
        injector = KeywordInjector()
        keywords = injector.extract_from_jd("一些无关文本")
        assert keywords == []

    def test_inject_missing_keywords(self):
        injector = KeywordInjector()
        resume = "# 简历\n\n## 技能\n- Python"
        result = injector.inject(resume, ["Docker", "Kubernetes"])
        assert "Docker" in result
        assert "Kubernetes" in result
        assert "ATS 关键词" in result

    def test_inject_no_missing(self):
        injector = KeywordInjector()
        resume = "# 简历\n\nPython Docker"
        result = injector.inject(resume, ["Python", "Docker"])
        assert result == resume


class TestPDFEngine:
    def test_simple_md_to_html(self):
        engine = PDFEngine()
        md = "# 标题\n## 副标题\n- 列表项\n正文"
        html = engine._simple_md_to_html(md)
        assert "<h1>标题</h1>" in html
        assert "<h2>副标题</h2>" in html
        assert "<li>列表项</li>" in html
        assert "<p>正文</p>" in html

    def test_md_to_html_skips_comments(self):
        engine = PDFEngine()
        md = "<!-- 注释 -->\n# 标题"
        html = engine._md_to_html(md)
        assert "注释" not in html
        assert "<h1>标题</h1>" in html

    def test_md_to_html_bold(self):
        engine = PDFEngine()
        md = "**加粗文本**"
        html = engine._simple_md_to_html(md)
        assert "<strong>加粗文本</strong>" in html
