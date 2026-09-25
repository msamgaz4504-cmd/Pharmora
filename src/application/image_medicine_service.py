from __future__ import annotations

from pathlib import Path

from src.application.medicine_service import MedicineService
from src.vision.medicine_identifier import MedicineImageIdentifier


class ImageMedicineService:
    def __init__(
        self,
        identifier: MedicineImageIdentifier | None = None,
        medicine_service: MedicineService | None = None,
    ):
        self.identifier = (
            identifier
            or MedicineImageIdentifier()
        )

        self.medicine_service = (
            medicine_service
            or MedicineService()
        )

    def identify_and_select(
        self,
        image_path: str | Path,
    ) -> dict:
        identification = (
            self.identifier.identify(
                image_path
            )
        )

        status = identification[
            "status"
        ]

        if status != "resolved":
            return {
                "status": status,
                "identification": identification,
                "selection": None,
                "profile": None,
            }

        resolution = identification[
            "resolution"
        ]

        medicine = resolution.get(
            "medicine"
        )

        if not isinstance(
            medicine,
            dict,
        ):
            raise RuntimeError(
                "Le médicament résolu "
                "ne contient pas de données valides."
            )

        cis = str(
            medicine.get(
                "cis",
                "",
            )
        ).strip()

        if not cis:
            raise RuntimeError(
                "Le médicament résolu "
                "ne contient pas de CIS."
            )

        selection = (
            self.medicine_service.select_by_cis(
                cis
            )
        )

        if selection.get(
            "status"
        ) != "selected":
            raise RuntimeError(
                "Le médicament identifié "
                "n'a pas pu être sélectionné."
            )

        return {
            "status": "resolved",
            "identification": identification,
            "selection": selection,
            "profile": (
                self.medicine_service.get_profile()
            ),
        }

    def get_profile(
        self,
    ) -> dict | None:
        return (
            self.medicine_service.get_profile()
        )

    def get_display_profile(
        self,
    ) -> dict | None:
        return (
            self.medicine_service.get_display_profile()
        )