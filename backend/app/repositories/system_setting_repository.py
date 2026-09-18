from collections.abc import Sequence

from app.models.system_setting import SystemSetting
from app.repositories.base import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    model = SystemSetting

    def get_by_key(self, key: str) -> SystemSetting | None:
        query = self._filter_by(self._query(), key=key)
        return self.session.execute(query).scalar_one_or_none()

    def upsert(self, key: str, value: str) -> SystemSetting:
        setting = self.get_by_key(key)
        if setting is not None:
            setting.value = value
            self.session.flush()
            return setting

        setting = SystemSetting(key=key, value=value)
        self.session.add(setting)
        self.session.flush()
        return setting

    def list_by_prefix(self, prefix: str) -> Sequence[SystemSetting]:
        """Every row whose key starts with `prefix` - ADR-178 keeps its
        runtime overrides under `runtime.` so they never collide with the
        table's other uses."""
        query = self._query().where(SystemSetting.key.startswith(prefix, autoescape=True))
        return self.session.execute(query).scalars().all()

    def delete(self, setting: SystemSetting) -> None:
        self.session.delete(setting)
        self.session.flush()
