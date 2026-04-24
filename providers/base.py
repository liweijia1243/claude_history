from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class HistoryProvider(ABC):
    id: str
    name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_dashboard_stats(self, range_str: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_recent_sessions(self, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self,
        page: int,
        limit: int,
        search: Optional[str],
        project: Optional[str],
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_projects(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_project(self, project_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self, project_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, project_id: str, session_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_subagent(self, project_id: str, session_id: str, agent_file: str) -> Dict[str, Any]:
        raise FileNotFoundError("Subagent not found")
