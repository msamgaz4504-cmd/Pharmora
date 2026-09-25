from __future__ import annotations


class MedicineProfile:
    def __init__(
        self,
        medicine: dict,
    ):
        if not isinstance(medicine, dict):
            raise TypeError(
                "medicine doit être un dictionnaire."
            )

        cis = str(
            medicine.get("cis", "")
        ).strip()

        name = str(
            medicine.get("name", "")
        ).strip()

        if not cis:
            raise ValueError(
                "Le CIS du médicament est absent."
            )

        if not name:
            raise ValueError(
                "Le nom du médicament est absent."
            )

        self._medicine = medicine

    @property
    def cis(self) -> str:
        return str(
            self._medicine.get(
                "cis",
                "",
            )
        ).strip()

    @property
    def name(self) -> str:
        return str(
            self._medicine.get(
                "name",
                "",
            )
        ).strip()

    @property
    def active_substances(self) -> list:
        substances = self._medicine.get(
            "active_substances",
            [],
        )

        return (
            substances
            if isinstance(
                substances,
                list,
            )
            else []
        )

    @property
    def strength(self) -> str | None:
        strengths = []

        for substance in self.active_substances:
            if not isinstance(
                substance,
                dict,
            ):
                continue

            strength = str(
                substance.get(
                    "strength",
                    "",
                )
            ).strip()

            if (
                strength
                and strength not in strengths
            ):
                strengths.append(
                    strength
                )

        if not strengths:
            return None

        return " / ".join(
            strengths
        )

    @property
    def pharmaceutical_form(
        self,
    ) -> str | None:
        value = self._medicine.get(
            "pharmaceutical_form"
        )

        if value is None:
            return None

        return str(value).strip() or None

    @property
    def administration_routes(
        self,
    ) -> list:
        routes = self._medicine.get(
            "administration_routes",
            [],
        )

        return (
            routes
            if isinstance(
                routes,
                list,
            )
            else []
        )

    @property
    def presentations(
        self,
    ) -> list:
        presentations = self._medicine.get(
            "presentations",
            [],
        )

        return (
            presentations
            if isinstance(
                presentations,
                list,
            )
            else []
        )

    @property
    def documents(
        self,
    ) -> list:
        documents = self._medicine.get(
            "documents",
            [],
        )

        return (
            documents
            if isinstance(
                documents,
                list,
            )
            else []
        )

    def to_dict(
        self,
    ) -> dict:
        return {
            "cis": self.cis,
            "name": self.name,
            "active_substances": (
                self.active_substances
            ),
            "strength": self.strength,
            "pharmaceutical_form": (
                self.pharmaceutical_form
            ),
            "administration_routes": (
                self.administration_routes
            ),
            "status": {
                "authorization": (
                    self._medicine.get(
                        "authorization_status"
                    )
                ),
                "commercialization": (
                    self._medicine.get(
                        "commercialization_status"
                    )
                ),
            },
            "presentations": (
                self.presentations
            ),
            "documents": (
                self.documents
            ),
        }

    def display_fields(
        self,
    ) -> dict:
        substance_names = []

        for substance in (
            self.active_substances
        ):
            if not isinstance(
                substance,
                dict,
            ):
                continue

            name = str(
                substance.get(
                    "substance_name",
                    "",
                )
            ).strip()

            if (
                name
                and name
                not in substance_names
            ):
                substance_names.append(
                    name
                )

        return {
            "cis": self.cis,
            "name": self.name,
            "strength": self.strength,
            "pharmaceutical_form": (
                self.pharmaceutical_form
            ),
            "administration_routes": (
                self.administration_routes
            ),
            "active_substances": (
                substance_names
            ),
            "authorization_status": (
                self._medicine.get(
                    "authorization_status"
                )
            ),
            "commercialization_status": (
                self._medicine.get(
                    "commercialization_status"
                )
            ),
        }