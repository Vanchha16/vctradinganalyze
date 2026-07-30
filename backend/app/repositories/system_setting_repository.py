from app.models.system_setting import SystemSetting
from app.repositories.base import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    model = SystemSetting

    def get_by_key(self, key: str) -> SystemSetting | None:
        query = self._filter_by(self._query(), key=key)
        return self.session.execute(query).scalar_one_or_none()
