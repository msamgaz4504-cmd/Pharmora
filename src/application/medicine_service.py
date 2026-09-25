from __future__ import annotations

from src.catalog.medicine_catalog import (
    MedicineCatalog,
)
from src.catalog.medicine_profile import (
    MedicineProfile,
)
from src.conversation.session import (
    ConversationSession,
)


class MedicineService:
    def __init__(
        self,
        catalog: MedicineCatalog | None = None,
    ):
        self.catalog = (
            catalog
            if catalog is not None
            else MedicineCatalog()
        )

        self._selected_medicine: dict | None = None
        self._session: ConversationSession | None = None

    @property
    def selected_medicine(
        self,
    ) -> dict | None:
        if self._selected_medicine is None:
            return None

        return dict(
            self._selected_medicine
        )

    @property
    def session(
        self,
    ) -> ConversationSession | None:
        return self._session

    @property
    def has_selection(self) -> bool:
        return self._selected_medicine is not None

    def search(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[dict]:
        return self.catalog.search(
            query=query,
            limit=limit,
        )

    def resolve(
        self,
        query: str,
    ) -> dict:
        return self.catalog.resolve(
            query
        )

    def select_by_cis(
        self,
        cis: str,
    ) -> dict:
        medicine = self.catalog.get_by_cis(
            cis
        )

        if medicine is None:
            return {
                "status": "not_found",
                "medicine": None,
                "profile": None,
            }

        return self._select(
            medicine
        )

    def select_from_query(
        self,
        query: str,
    ) -> dict:
        resolution = self.resolve(
            query
        )

        if resolution["status"] != "resolved":
            return {
                "status": resolution["status"],
                "medicine": None,
                "profile": None,
                "matches": resolution["matches"],
            }

        selection = self._select(
            resolution["medicine"]
        )

        selection["matches"] = (
            resolution["matches"]
        )

        return selection

    def get_profile(
        self,
    ) -> dict | None:
        if self._selected_medicine is None:
            return None

        return MedicineProfile(
            self._selected_medicine
        ).to_dict()

    def get_display_profile(
        self,
    ) -> dict | None:
        if self._selected_medicine is None:
            return None

        return MedicineProfile(
            self._selected_medicine
        ).display_fields()

    def clear_selection(
        self,
    ) -> None:
        self._selected_medicine = None
        self._session = None

    def clear_conversation(
        self,
    ) -> None:
        if self._session is not None:
            self._session.clear()

    def _select(
        self,
        medicine: dict,
    ) -> dict:
        profile = MedicineProfile(
            medicine
        )

        previous_cis = None

        if self._selected_medicine is not None:
            previous_cis = str(
                self._selected_medicine.get(
                    "cis",
                    self._selected_medicine.get(
                        "CIS",
                        "",
                    ),
                )
            ).strip()

        medicine_changed = (
            previous_cis != profile.cis
        )

        self._selected_medicine = dict(
            medicine
        )

        if self._session is None:
            self._session = ConversationSession(
                cis=profile.cis,
                medicine_name=profile.name,
            )

        elif medicine_changed:
            self._session.change_medicine(
                cis=profile.cis,
                medicine_name=profile.name,
                clear_history=True,
            )

        return {
            "status": "selected",
            "medicine": dict(
                medicine
            ),
            "profile": profile.to_dict(),
        }