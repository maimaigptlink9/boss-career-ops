from __future__ import annotations

from typing import Any

from boss_career_ops.platform.models import Job


def extract_jd_text(job: Job | dict[str, Any]) -> str:
    job = Job.normalize(job)
    parts = [
        job.job_name,
        ",".join(job.job_labels) if job.job_labels else "",
        ",".join(job.skills) if job.skills else "",
        job.experience,
        job.education,
        job.description,
    ]
    return " ".join(str(p) for p in parts if p)
