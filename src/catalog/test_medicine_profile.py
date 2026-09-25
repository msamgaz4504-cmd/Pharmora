from __future__ import annotations

from src.catalog.medicine_catalog import (
    MedicineCatalog,
)
from src.catalog.medicine_profile import (
    MedicineProfile,
)


DOLIPRANE_CIS = "67119691"
DOLIPRANE_NAME = (
    "DOLIPRANE 500 mg, gélule"
)

IBUPROFENE_CIS = "63691015"


def check(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(
            message
        )


def get_profile(
    catalog: MedicineCatalog,
    cis: str,
) -> MedicineProfile:
    medicine = catalog.get_by_cis(
        cis
    )

    check(
        medicine is not None,
        f"Médicament introuvable : {cis}",
    )

    return MedicineProfile(
        medicine
    )


def test_identity(
    catalog: MedicineCatalog,
) -> None:
    profile = get_profile(
        catalog,
        DOLIPRANE_CIS,
    )

    check(
        profile.cis
        == DOLIPRANE_CIS,
        "CIS incorrect.",
    )

    check(
        profile.name
        == DOLIPRANE_NAME,
        "Nom incorrect.",
    )


def test_structured_profile(
    catalog: MedicineCatalog,
) -> None:
    profile = get_profile(
        catalog,
        DOLIPRANE_CIS,
    )

    data = profile.to_dict()

    expected_keys = {
        "cis",
        "name",
        "active_substances",
        "strength",
        "pharmaceutical_form",
        "administration_routes",
        "status",
        "presentations",
        "documents",
    }

    check(
        set(data.keys())
        == expected_keys,
        "Structure de fiche incorrecte.",
    )

    check(
        data["cis"]
        == DOLIPRANE_CIS,
        "CIS incorrect dans to_dict.",
    )

    check(
        data["name"]
        == DOLIPRANE_NAME,
        "Nom incorrect dans to_dict.",
    )


def test_list_fields(
    catalog: MedicineCatalog,
) -> None:
    profile = get_profile(
        catalog,
        DOLIPRANE_CIS,
    )

    check(
        isinstance(
            profile.active_substances,
            list,
        ),
        "active_substances doit "
        "être une liste.",
    )

    check(
        isinstance(
            profile.administration_routes,
            list,
        ),
        "administration_routes doit "
        "être une liste.",
    )

    check(
        isinstance(
            profile.presentations,
            list,
        ),
        "presentations doit "
        "être une liste.",
    )

    check(
        isinstance(
            profile.documents,
            list,
        ),
        "documents doit "
        "être une liste.",
    )


def test_display_fields(
    catalog: MedicineCatalog,
) -> None:
    profile = get_profile(
        catalog,
        DOLIPRANE_CIS,
    )

    display = (
        profile.display_fields()
    )

    expected_keys = {
        "name",
        "cis",
        "active_substances",
        "strength",
        "pharmaceutical_form",
        "administration_routes",
        "status",
    }

    check(
        set(display.keys())
        == expected_keys,
        "Champs UI incorrects.",
    )

    for key, value in display.items():
        check(
            isinstance(
                value,
                str,
            ),
            f"{key} doit être "
            "directement affichable.",
        )

        check(
            bool(
                value.strip()
            ),
            f"{key} est vide.",
        )


def test_second_medicine(
    catalog: MedicineCatalog,
) -> None:
    profile = get_profile(
        catalog,
        IBUPROFENE_CIS,
    )

    check(
        profile.cis
        == IBUPROFENE_CIS,
        "CIS ibuprofène incorrect.",
    )

    check(
        "IBUPROFENE"
        in profile.name.upper(),
        "Nom ibuprofène incorrect.",
    )


def test_missing_optional_fields() -> None:
    profile = MedicineProfile(
        {
            "cis": "12345678",
            "name": "MEDICAMENT TEST",
        }
    )

    check(
        profile.active_substances
        == [],
        "Substances absentes "
        "doivent donner [].",
    )

    check(
        profile.strength is None,
        "Dosage absent doit "
        "donner None.",
    )

    check(
        profile.pharmaceutical_form
        is None,
        "Forme absente doit "
        "donner None.",
    )

    check(
        profile.administration_routes
        == [],
        "Voies absentes doivent "
        "donner [].",
    )

    display = (
        profile.display_fields()
    )

    check(
        display[
            "active_substances"
        ]
        == "Non renseigné",
        "Fallback UI incorrect.",
    )

    check(
        display[
            "pharmaceutical_form"
        ]
        == "Non renseignée",
        "Fallback forme incorrect.",
    )


def test_invalid_identity() -> None:
    errors = 0

    try:
        MedicineProfile(
            {}
        )
    except ValueError:
        errors += 1

    try:
        MedicineProfile(
            {
                "cis": "123",
                "name": "",
            }
        )
    except ValueError:
        errors += 1

    try:
        MedicineProfile(
            []
        )
    except TypeError:
        errors += 1

    check(
        errors == 3,
        "Les identités invalides "
        "ne sont pas toutes rejetées.",
    )


def test_copy_isolation(
    catalog: MedicineCatalog,
) -> None:
    medicine = catalog.get_by_cis(
        DOLIPRANE_CIS
    )

    check(
        medicine is not None,
        "DOLIPRANE introuvable.",
    )

    profile = MedicineProfile(
        medicine
    )

    original_name = profile.name

    medicine["name"] = (
        "MODIFICATION EXTERNE"
    )

    check(
        profile.name
        == original_name,
        "La fiche ne doit pas être "
        "modifiée par référence externe.",
    )


def main() -> None:
    catalog = MedicineCatalog()

    tests = [
        test_identity,
        test_structured_profile,
        test_list_fields,
        test_display_fields,
        test_second_medicine,
        test_missing_optional_fields,
        test_invalid_identity,
        test_copy_isolation,
    ]

    passed = 0

    print("=" * 72)
    print(
        "PHARMORA - TEST MEDICINE PROFILE"
    )
    print("=" * 72)

    for test in tests:
        try:
            if test in (
                test_missing_optional_fields,
                test_invalid_identity,
            ):
                test()
            else:
                test(
                    catalog
                )

            passed += 1

            print(
                f"PASS - {test.__name__}"
            )

        except Exception as error:
            print(
                f"FAIL - {test.__name__}"
            )

            print(
                f"       "
                f"{type(error).__name__}: "
                f"{error}"
            )

    print()
    print("=" * 72)
    print("RESULTATS")
    print("=" * 72)

    print(
        f"PASS : "
        f"{passed}/{len(tests)}"
    )

    if passed == len(tests):
        print(
            "STATUS FINAL : PASS"
        )
    else:
        print(
            "STATUS FINAL : REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()