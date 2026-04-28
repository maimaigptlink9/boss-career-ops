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
        result = gen.generate({"job_name": "Golang"})
        assert result == ""

    def test_generate_from_cv(self):
        cv = "# 简历\n\n## 技能\n- Python\n- Go"
        gen = self._make_generator(cv_content=cv)
        result = gen.generate({"job_name": "Golang", "company_name": "公司", "skills": "Go,Kubernetes"})
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

    def test_generate_uses_snake_case_fields(self):
        cv = "# 简历\n\n## 技能\n- Python"
        gen = self._make_generator(cv_content=cv)
        result = gen.generate({"job_name": "Golang", "company_name": "测试公司", "skills": "Go", "description": "后端开发"})
        assert "Golang" in result
        assert "测试公司" in result

    def test_extract_jd_text_snake_case(self):
        gen = self._make_generator()
        jd_text = gen._extract_jd_text({"job_name": "Python开发", "skills": "Python,Go", "description": "后端开发", "job_labels": ["远程"]})
        assert "Python开发" in jd_text


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
        assert 'class="ats-keywords"' in result

    def test_inject_no_missing(self):
        injector = KeywordInjector()
        resume = "# 简历\n\nPython Docker"
        result = injector.inject(resume, ["Python", "Docker"])
        assert result == resume


class TestPDFEngine:
    def test_md_to_html_skips_comments(self):
        engine = PDFEngine()
        md = "# 标题"
        html = engine._md_to_html(md)
        assert "<h1>标题</h1>" in html

    def test_md_to_html_bold(self):
        engine = PDFEngine()
        md = "**加粗文本**"
        html = engine._md_to_html(md)
        assert "<strong>加粗文本</strong>" in html
