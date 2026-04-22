from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from boss_career_ops.platform.models import (
    AuthStatus,
    ChatMessage,
    Contact,
    Job,
    OperationResult,
)


class PlatformAdapter(ABC):

    @abstractmethod
    def search(self, params: dict[str, Any]) -> list[Job]:
        ...

    @abstractmethod
    def get_job_detail(self, security_id: str) -> Job | None:
        ...

    @abstractmethod
    def greet(self, security_id: str, job_id: str) -> OperationResult:
        ...

    @abstractmethod
    def apply(self, security_id: str, job_id: str) -> OperationResult:
        ...

    @abstractmethod
    def get_chat_list(self) -> list[Contact]:
        ...

    @abstractmethod
    def get_chat_messages(self, security_id: str) -> list[ChatMessage]:
        ...

    @abstractmethod
    def exchange_contact(self, security_id: str, contact_type: str) -> OperationResult:
        ...

    @abstractmethod
    def mark_contact(self, security_id: str, tag: str) -> OperationResult:
        ...

    @abstractmethod
    def get_recommendations(self, params: dict[str, Any] | None = None) -> list[Job]:
        ...

    @abstractmethod
    def upload_resume(self, pdf_path: str, display_name: str) -> OperationResult:
        ...

    @abstractmethod
    def login(self, *, profile: str = "") -> AuthStatus:
        ...

    @abstractmethod
    def check_auth_status(self) -> AuthStatus:
        ...

    @abstractmethod
    def build_search_params(
        self,
        keyword: str,
        city: str = "",
        experience: str = "",
        education: str = "",
        job_type: str = "",
        scale: str = "",
        finance: str = "",
        page: int = 1,
        page_size: int = 15,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_city_code(self, city: str) -> str:
        ...

    @abstractmethod
    def filter_by_welfare(self, jobs: list[Job], welfare_keywords: str) -> list[Job]:
        ...


class PlatformBrowser(ABC):

    @abstractmethod
    def ensure_connected(self) -> bool:
        ...

    @abstractmethod
    def get_page(self):
        ...

    @abstractmethod
    def add_cookies(self, cookies: list[dict]) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @abstractmethod
    def get_anti_redirect_js(self) -> str:
        ...
