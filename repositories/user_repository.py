"""Data access for :class:`models.user.User`."""
from __future__ import annotations

from models.user import User

from .base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_username(self, username: str) -> User | None:
        return (
            self._base_query()
            .filter(User.username == username)
            .first()
        )

    def exists_username(self, username: str) -> bool:
        return self.get_by_username(username) is not None
