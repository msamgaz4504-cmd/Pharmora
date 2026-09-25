from __future__ import annotations

from src.catalog.medicine_catalog import (
    MedicineCatalog,
)


DOLIPRANE_CAPSULE_CIS = "67119691"
DOLIPRANE_CAPSULE_NAME = (
    "DOLIPRANE 500 mg, gélule"
)

IBUPROFENE_GEL_CIS = "63691015"
IBUPROFENE_GEL_NAME = (
    "IBUPROFENE ARROW 5 %, gel"
)

AMOXICILLIN_CIS = "67459306"
AMOXICILLIN_NAME = (
    "AMOXICILLINE BENTA 500 mg, gélule"
)


def check(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(
            message
        )


def medicine_name(
    medicine: dict,
) -> str:
    for key in (
        "name",
        "medicine_name",
        "denomination",
    ):
        value = medicine.get(
            key
        )

        if value:
            return str(
                value
            ).strip()

    return ""


def medicine_cis(
    medicine: dict,
) -> str:
    for key in (
        "cis",
        "CIS",
        "cis_code",
    ):
        value = medicine.get(
            key
        )

        if value is not None:
            return str(
                value
            ).strip()

    return ""


def test_catalog_load(
    catalog: MedicineCatalog,
) -> None:
    check(
        catalog.count == 15,
        "Le corpus validé doit contenir "
        "15 médicaments.",
    )


def test_get_by_cis(
    catalog: MedicineCatalog,
) -> None:
    medicine = catalog.get_by_cis(
        DOLIPRANE_CAPSULE_CIS
    )

    check(
        medicine is not None,
        "DOLIPRANE introuvable par CIS.",
    )

    check(
        medicine_name(
            medicine
        )
        == DOLIPRANE_CAPSULE_NAME,
        "Mauvais médicament retourné.",
    )

    check(
        catalog.get_by_cis(
            "00000000"
        )
        is None,
        "Un CIS inexistant doit "
        "retourner None.",
    )


def test_exact_resolution(
    catalog: MedicineCatalog,
) -> None:
    result = catalog.resolve(
        DOLIPRANE_CAPSULE_NAME
    )

    check(
        result["status"]
        == "resolved",
        "La dénomination exacte doit "
        "être résolue.",
    )

    check(
        medicine_cis(
            result["medicine"]
        )
        == DOLIPRANE_CAPSULE_CIS,
        "CIS DOLIPRANE incorrect.",
    )


def test_case_and_accents(
    catalog: MedicineCatalog,
) -> None:
    result = catalog.resolve(
        "doliprane 500 MG gelule"
    )

    check(
        result["status"]
        == "resolved",
        "La casse et les accents "
        "ne doivent pas empêcher "
        "la résolution.",
    )

    check(
        medicine_cis(
            result["medicine"]
        )
        == DOLIPRANE_CAPSULE_CIS,
        "Mauvaise spécialité résolue.",
    )


def test_ibuprofen_search(
    catalog: MedicineCatalog,
) -> None:
    matches = catalog.search(
        "ibuprofene gel"
    )

    check(
        len(matches) >= 1,
        "La recherche ibuprofene gel "
        "ne retourne aucun résultat.",
    )

    cis_values = {
        medicine_cis(
            medicine
        )
        for medicine in matches
    }

    check(
        IBUPROFENE_GEL_CIS
        in cis_values,
        "IBUPROFENE ARROW gel "
        "doit être candidat.",
    )


def test_amoxicillin_search(
    catalog: MedicineCatalog,
) -> None:
    matches = catalog.search(
        "amoxicilline 500"
    )

    check(
        len(matches) >= 1,
        "La recherche amoxicilline 500 "
        "ne retourne aucun résultat.",
    )

    cis_values = {
        medicine_cis(
            medicine
        )
        for medicine in matches
    }

    check(
        AMOXICILLIN_CIS
        in cis_values,
        "AMOXICILLINE BENTA "
        "doit être candidate.",
    )


def test_doliprane_ambiguity(
    catalog: MedicineCatalog,
) -> None:
    result = catalog.resolve(
        "doliprane 500 mg"
    )

    check(
        result["status"]
        == "ambiguous",
        "DOLIPRANE 500 mg doit rester "
        "ambigu dans notre catalogue.",
    )

    check(
        result["medicine"]
        is None,
        "Une recherche ambiguë ne doit "
        "pas sélectionner arbitrairement "
        "un médicament.",
    )

    check(
        len(
            result["matches"]
        ) >= 2,
        "Plusieurs spécialités "
        "DOLIPRANE 500 mg sont attendues.",
    )


def test_not_found(
    catalog: MedicineCatalog,
) -> None:
    result = catalog.resolve(
        "medicament totalement inexistant xyz"
    )

    check(
        result["status"]
        == "not_found",
        "Une recherche inexistante doit "
        "retourner not_found.",
    )

    check(
        result["medicine"]
        is None,
        "Aucun médicament ne doit "
        "être sélectionné.",
    )

    check(
        result["matches"]
        == [],
        "La liste des candidats "
        "doit être vide.",
    )


def test_empty_query(
    catalog: MedicineCatalog,
) -> None:
    result = catalog.resolve(
        "   "
    )

    check(
        result["status"]
        == "not_found",
        "Une requête vide doit "
        "retourner not_found.",
    )

    check(
        catalog.search(
            "   "
        )
        == [],
        "search vide doit "
        "retourner [].",
    )


def test_limit(
    catalog: MedicineCatalog,
) -> None:
    matches = catalog.search(
        "doliprane",
        limit=1,
    )

    check(
        len(matches) <= 1,
        "La limite de recherche "
        "n'est pas respectée.",
    )


def test_normalization() -> None:
    normalized = (
        MedicineCatalog.normalize(
            "  IBUPROFÈNE   ARROW 5 %, GEL "
        )
    )

    check(
        normalized
        == "ibuprofene arrow 5 gel",
        "Normalisation incorrecte.",
    )


def main() -> None:
    catalog = MedicineCatalog()

    tests = [
        test_catalog_load,
        test_get_by_cis,
        test_exact_resolution,
        test_case_and_accents,
        test_ibuprofen_search,
        test_amoxicillin_search,
        test_doliprane_ambiguity,
        test_not_found,
        test_empty_query,
        test_limit,
    ]

    passed = 0

    print("=" * 72)
    print(
        "PHARMORA - TEST MEDICINE CATALOG"
    )
    print("=" * 72)
    print(
        f"Médicaments chargés : "
        f"{catalog.count}"
    )

    for test in tests:
        try:
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

    try:
        test_normalization()

        passed += 1

        print(
            "PASS - test_normalization"
        )

    except Exception as error:
        print(
            "FAIL - test_normalization"
        )

        print(
            f"       "
            f"{type(error).__name__}: "
            f"{error}"
        )

    total = (
        len(tests)
        + 1
    )

    print()
    print("=" * 72)
    print("RESULTATS")
    print("=" * 72)
    print(
        f"PASS : {passed}/{total}"
    )

    if passed == total:
        print(
            "STATUS FINAL : PASS"
        )
    else:
        print(
            "STATUS FINAL : REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()