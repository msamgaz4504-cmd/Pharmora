from __future__ import annotations

from src.application.medicine_service import (
    MedicineService,
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


def test_initial_state() -> None:
    service = MedicineService()

    check(
        not service.has_selection,
        "Aucun médicament ne doit "
        "être sélectionné au départ.",
    )

    check(
        service.selected_medicine is None,
        "selected_medicine doit être None.",
    )

    check(
        service.session is None,
        "La session doit être None.",
    )

    check(
        service.get_profile() is None,
        "La fiche doit être None.",
    )


def test_search() -> None:
    service = MedicineService()

    results = service.search(
        "doliprane"
    )

    check(
        len(results) >= 1,
        "DOLIPRANE doit être trouvé.",
    )


def test_ambiguous_query() -> None:
    service = MedicineService()

    result = service.select_from_query(
        "doliprane 500 mg"
    )

    check(
        result["status"]
        == "ambiguous",
        "La requête doit rester ambiguë.",
    )

    check(
        not service.has_selection,
        "Une ambiguïté ne doit pas "
        "sélectionner un médicament.",
    )

    check(
        len(result["matches"]) >= 2,
        "Plusieurs candidats sont attendus.",
    )


def test_exact_query_selection() -> None:
    service = MedicineService()

    result = service.select_from_query(
        DOLIPRANE_NAME
    )

    check(
        result["status"]
        == "selected",
        "La spécialité exacte doit "
        "être sélectionnée.",
    )

    check(
        service.has_selection,
        "Une sélection est attendue.",
    )

    check(
        result["profile"]["cis"]
        == DOLIPRANE_CIS,
        "CIS incorrect.",
    )

    check(
        service.session is not None,
        "La session doit être créée.",
    )

    check(
        service.session.cis
        == DOLIPRANE_CIS,
        "La session utilise "
        "le mauvais CIS.",
    )


def test_select_by_cis() -> None:
    service = MedicineService()

    result = service.select_by_cis(
        DOLIPRANE_CIS
    )

    check(
        result["status"]
        == "selected",
        "Sélection CIS échouée.",
    )

    check(
        result["profile"]["name"]
        == DOLIPRANE_NAME,
        "Mauvais médicament.",
    )


def test_unknown_cis() -> None:
    service = MedicineService()

    result = service.select_by_cis(
        "00000000"
    )

    check(
        result["status"]
        == "not_found",
        "Un CIS inconnu doit retourner "
        "not_found.",
    )

    check(
        not service.has_selection,
        "Aucune sélection ne doit "
        "être créée.",
    )


def test_profile() -> None:
    service = MedicineService()

    service.select_by_cis(
        DOLIPRANE_CIS
    )

    profile = service.get_profile()
    display = (
        service.get_display_profile()
    )

    check(
        profile is not None,
        "Fiche structurée absente.",
    )

    check(
        display is not None,
        "Fiche UI absente.",
    )

    check(
        profile["cis"]
        == DOLIPRANE_CIS,
        "CIS incorrect dans la fiche.",
    )

    check(
        display["name"]
        == DOLIPRANE_NAME,
        "Nom UI incorrect.",
    )


def test_same_medicine_keeps_history() -> None:
    service = MedicineService()

    service.select_by_cis(
        DOLIPRANE_CIS
    )

    check(
        service.session is not None,
        "Session absente.",
    )

    service.session.add_user_message(
        "Question sur le Doliprane"
    )

    service.session.add_assistant_message(
        "Réponse sur le Doliprane"
    )

    service.select_by_cis(
        DOLIPRANE_CIS
    )

    check(
        service.session.message_count == 2,
        "Resélectionner le même médicament "
        "ne doit pas supprimer "
        "la conversation.",
    )


def test_change_medicine_clears_history() -> None:
    service = MedicineService()

    service.select_by_cis(
        DOLIPRANE_CIS
    )

    check(
        service.session is not None,
        "Session absente.",
    )

    service.session.add_user_message(
        "Question Doliprane"
    )

    service.session.add_assistant_message(
        "Réponse Doliprane"
    )

    result = service.select_by_cis(
        IBUPROFENE_CIS
    )

    check(
        result["status"]
        == "selected",
        "IBUPROFENE doit être sélectionné.",
    )

    check(
        service.session.cis
        == IBUPROFENE_CIS,
        "La session n'a pas changé "
        "de médicament.",
    )

    check(
        service.session.is_empty(),
        "Changer de médicament doit "
        "vider la conversation.",
    )


def test_clear_conversation() -> None:
    service = MedicineService()

    service.select_by_cis(
        DOLIPRANE_CIS
    )

    service.session.add_user_message(
        "Question"
    )

    service.session.add_assistant_message(
        "Réponse"
    )

    service.clear_conversation()

    check(
        service.session.is_empty(),
        "La conversation doit être vide.",
    )

    check(
        service.has_selection,
        "Le médicament doit rester "
        "sélectionné.",
    )


def test_clear_selection() -> None:
    service = MedicineService()

    service.select_by_cis(
        DOLIPRANE_CIS
    )

    service.clear_selection()

    check(
        not service.has_selection,
        "La sélection doit être supprimée.",
    )

    check(
        service.session is None,
        "La session doit être supprimée.",
    )

    check(
        service.get_profile() is None,
        "La fiche doit être supprimée.",
    )


def main() -> None:
    tests = [
        test_initial_state,
        test_search,
        test_ambiguous_query,
        test_exact_query_selection,
        test_select_by_cis,
        test_unknown_cis,
        test_profile,
        test_same_medicine_keeps_history,
        test_change_medicine_clears_history,
        test_clear_conversation,
        test_clear_selection,
    ]

    passed = 0

    print("=" * 72)
    print(
        "PHARMORA - TEST MEDICINE SERVICE"
    )
    print("=" * 72)

    for test in tests:
        try:
            test()

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
        f"PASS : {passed}/{len(tests)}"
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