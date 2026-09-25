from src.retrieval.search import PharmoraRetriever


TESTS = [
    {
        "question": "Dans quels cas utilise-t-on ce médicament ?",
        "cis": "67119691",
        "expected": "4.1",
    },
    {
        "question": "À quoi sert ce traitement ?",
        "cis": "67119691",
        "expected": "4.1",
    },
    {
        "question": "Pourquoi pourrait-on me donner ce médicament ?",
        "cis": "67119691",
        "expected": "4.1",
    },
    {
        "question": "Quelle est la posologie et comment le prendre ?",
        "cis": "67119691",
        "expected": "4.2",
    },
    {
        "question": "Comment dois-je l'utiliser ?",
        "cis": "63691015",
        "expected": "4.2",
    },
    {
        "question": "Quelle quantité faut-il utiliser et à quelle fréquence ?",
        "cis": "63691015",
        "expected": "4.2",
    },
    {
        "question": "Dans quels cas ce médicament est-il contre-indiqué ?",
        "cis": "67119691",
        "expected": "4.3",
    },
    {
        "question": "Quand ne faut-il surtout pas prendre ce médicament ?",
        "cis": "67119691",
        "expected": "4.3",
    },
    {
        "question": "Y a-t-il des situations où ce médicament ne doit pas être utilisé ?",
        "cis": "63691015",
        "expected": "4.3",
    },
    {
        "question": "Quelles précautions faut-il prendre avec ce médicament ?",
        "cis": "67119691",
        "expected": "4.4",
    },
    {
        "question": "À quoi dois-je faire attention avant de l'utiliser ?",
        "cis": "63691015",
        "expected": "4.4",
    },
    {
        "question": "Est-ce qu'il y a des choses importantes à savoir avant de le prendre ?",
        "cis": "67119691",
        "expected": "4.4",
    },
    {
        "question": "Quelles sont les interactions avec les autres médicaments ?",
        "cis": "67119691",
        "expected": "4.5",
    },
    {
        "question": "Est-ce que ce médicament peut poser problème avec un autre traitement ?",
        "cis": "67459306",
        "expected": "4.5",
    },
    {
        "question": "Peut-on utiliser ce médicament pendant la grossesse ?",
        "cis": "63691015",
        "expected": "4.6",
    },
    {
        "question": "Une femme enceinte peut-elle utiliser ce produit ?",
        "cis": "63691015",
        "expected": "4.6",
    },
    {
        "question": "Est-ce compatible avec l'allaitement ?",
        "cis": "63691015",
        "expected": "4.6",
    },
    {
        "question": "Quels sont les effets indésirables de ce médicament ?",
        "cis": "67119691",
        "expected": "4.8",
    },
    {
        "question": "Quels problèmes peuvent apparaître après avoir pris ce médicament ?",
        "cis": "67119691",
        "expected": "4.8",
    },
    {
        "question": "Est-ce que ce traitement peut provoquer des réactions gênantes ?",
        "cis": "67459306",
        "expected": "4.8",
    },
    {
        "question": "À quoi sert cet antibiotique ?",
        "cis": "67459306",
        "expected": "4.1",
    },
    {
        "question": "Pour quelles infections est-ce qu'on utilise cet antibiotique ?",
        "cis": "67459306",
        "expected": "4.1",
    },
    {
        "question": "Dans quels cas cet antibiotique est-il utilisé ?",
        "cis": "67459306",
        "expected": "4.1",
    },
]


def main():
    print(
        "\n=== PHARMORA SEMANTIC RETRIEVAL EVALUATION ===\n"
    )

    retriever = PharmoraRetriever()

    top1_success = 0
    top3_success = 0

    for index, test in enumerate(
        TESTS,
        start=1,
    ):
        results = retriever.search(
            question=test["question"],
            cis=test["cis"],
            document_type="RCP",
            top_k=5,
            candidate_k=20,
        )

        sections = [
            str(result["section_number"])
            for result in results
        ]

        top1_pass = (
            bool(sections)
            and sections[0]
            == test["expected"]
        )

        top3_pass = (
            test["expected"]
            in sections[:3]
        )

        if top1_pass:
            top1_success += 1

        if top3_pass:
            top3_success += 1

        status = (
            "PASS"
            if top3_pass
            else "FAIL"
        )

        print(
            f"[{index}] {status}"
        )

        print(
            f"Question: {test['question']}"
        )

        print(
            f"Expected: {test['expected']}"
        )

        for rank, result in enumerate(
            results,
            start=1,
        ):
            print(
                f"  #{rank} "
                f"{result['section_number']} "
                f"{result['section_title']} "
                f"| dense="
                f"{result['dense_score']:.4f} "
                f"| reranker="
                f"{result['reranker_score']:.4f}"
            )

        print()

    total = len(TESTS)

    top1_rate = (
        top1_success
        / total
        * 100
    )

    top3_rate = (
        top3_success
        / total
        * 100
    )

    print(
        "=== RESULTS ==="
    )

    print(
        f"Top-1: "
        f"{top1_success}/{total} "
        f"({top1_rate:.1f}%)"
    )

    print(
        f"Top-3: "
        f"{top3_success}/{total} "
        f"({top3_rate:.1f}%)"
    )

    if top3_rate >= 90:
        print(
            "FINAL STATUS: PASS"
        )
    else:
        print(
            "FINAL STATUS: REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()