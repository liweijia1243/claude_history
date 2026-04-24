from abc import ABC, abstractmethod
from typing import Optional


class HistoryProvider(ABC):
    id: str
    name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_dashboard_stats(self, range_str: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_recent_sessions(self, limit: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self,
        page: int,
        limit: int,
        search: Optional[str],
        project: Optional[str],
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_projects(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_project(self, project_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self, project_id: str) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, project_id: str, session_id: str) -> dict:
        raise NotImplementedError

    def get_subagent(self, project_id: str, session_id: str, agent_file: str) -> dict:
        raise FileNotFoundError("Subagent not found")
