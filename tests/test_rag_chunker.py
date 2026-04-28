from boss_career_ops.rag.chunker import chunk_jd, chunk_resume, chunk_interview, MAX_JD_CHUNK_LENGTH
from boss_career_ops.rag.schemas import JDDocument, ResumeTemplate, InterviewExperience


class TestChunkJd:
    def test_returns_single_chunk_with_correct_metadata(self):
        doc = JDDocument(
            doc_id="jd001",
            content="高级Python开发，负责后端架构设计",
            job_name="高级Python开发",
            company_name="测试科技",
            city="深圳",
            salary_min=20000,
            salary_max=40000,
            skills=["Python", "Go", "Docker"],
            industry="互联网",
            score=4.2,
            grade="B",
        )
        chunks = chunk_jd(doc)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "高级Python开发，负责后端架构设计"
        meta = chunks[0]["metadata"]
        assert meta["doc_id"] == "jd001"
        assert meta["job_name"] == "高级Python开发"
        assert meta["company_name"] == "测试科技"
        assert meta["city"] == "深圳"
        assert meta["salary_min"] == 20000
        assert meta["salary_max"] == 40000
        assert meta["skills"] == "Python,Go,Docker"
        assert meta["industry"] == "互联网"
        assert meta["score"] == 4.2
        assert meta["grade"] == "B"

    def test_short_text_kept_intact(self):
        doc = JDDocument(
            doc_id="jd_short",
            content="简短JD",
            job_name="开发",
            company_name="公司",
            city="北京",
            salary_min=10000,
            salary_max=20000,
            skills=["Python"],
            industry="互联网",
        )
        chunks = chunk_jd(doc)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "简短JD"

    def test_long_text_splits_into_chunks(self):
        para = "A" * 3000
        long_content = "\n\n".join([para, para, para])
        doc = JDDocument(
            doc_id="jd_long",
            content=long_content,
            job_name="开发",
            company_name="公司",
            city="北京",
            salary_min=10000,
            salary_max=20000,
            skills=["Python"],
            industry="互联网",
        )
        chunks = chunk_jd(doc)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk["content"]) <= MAX_JD_CHUNK_LENGTH
        for i, chunk in enumerate(chunks):
            assert chunk["metadata"]["chunk_index"] == i
            assert chunk["metadata"]["doc_id"] == "jd_long"

    def test_very_long_single_paragraph_splits(self):
        single_para = "X" * (MAX_JD_CHUNK_LENGTH + 1000)
        doc = JDDocument(
            doc_id="jd_huge",
            content=single_para,
            job_name="开发",
            company_name="公司",
            city="北京",
            salary_min=10000,
            salary_max=20000,
            skills=["Python"],
            industry="互联网",
        )
        chunks = chunk_jd(doc)
        assert len(chunks) == 2
        assert len(chunks[0]["content"]) == MAX_JD_CHUNK_LENGTH
        assert len(chunks[1]["content"]) == 1000


class TestChunkResume:
    def test_splits_by_headers(self):
        doc = ResumeTemplate(
            doc_id="resume001",
            content="## 工作经历\n- 公司A\n## 教育背景\n- 大学B",
            job_name="Python开发",
            company_name="测试公司",
            result="通过",
            keywords=["Python", "FastAPI"],
        )
        chunks = chunk_resume(doc)
        assert len(chunks) == 2
        assert chunks[0]["metadata"]["section_name"] == "工作经历"
        assert chunks[1]["metadata"]["section_name"] == "教育背景"
        for chunk in chunks:
            assert chunk["metadata"]["doc_id"] == "resume001"
            assert chunk["metadata"]["keywords"] == "Python,FastAPI"

    def test_no_headers_returns_full_content(self):
        doc = ResumeTemplate(
            doc_id="resume002",
            content="这是没有标题的简历内容",
            job_name="Go开发",
            company_name="另一公司",
            result="待定",
            keywords=[],
        )
        chunks = chunk_resume(doc)
        assert len(chunks) == 1
        assert chunks[0]["metadata"]["section_name"] == "概述"


class TestChunkInterview:
    def test_returns_single_chunk(self):
        doc = InterviewExperience(
            doc_id="intv001",
            content="面试经验：三轮技术面",
            company_name="大厂",
            job_name="架构师",
            questions=["系统设计", "并发编程"],
            result="通过",
        )
        chunks = chunk_interview(doc)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "面试经验：三轮技术面"
        meta = chunks[0]["metadata"]
        assert meta["doc_id"] == "intv001"
        assert meta["company_name"] == "大厂"
        assert meta["job_name"] == "架构师"
        assert meta["questions"] == "系统设计|并发编程"
        assert meta["result"] == "通过"
