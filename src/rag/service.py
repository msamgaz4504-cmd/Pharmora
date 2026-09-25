from __future__ import annotations

import re
import unicodedata

from src.rag.evidence import EvidenceSelector
from src.rag.generator import PharmoraGenerator
from src.rag.query_rewriter import QueryRewriter
from src.retrieval.search import PharmoraRetriever


RETRIEVAL_CANDIDATE_K = 15


class PharmoraRAG:
    def __init__(self):
        self.retriever = PharmoraRetriever()
        self.evidence_selector = EvidenceSelector()
        self.query_rewriter = QueryRewriter()
        self.generator = PharmoraGenerator()

    def ask(
        self,
        question: str,
        cis: str,
        medicine_name: str,
    ) -> dict:
        return self.answer(
            question=question,
            cis=cis,
            medicine_name=medicine_name,
        )

    def answer(
        self,
        question: str,
        cis: str,
        medicine_name: str,
    ) -> dict:
        question = question.strip()

        if not question:
            raise ValueError(
                "La question est vide."
            )

        candidates = self._retrieve(
            query=question,
            cis=cis,
        )

        if not candidates:
            return self._insufficient_response(
                reason=(
                    "Aucun passage correspondant "
                    "au médicament n'a été trouvé."
                ),
                candidates=[],
                retrieval_query=question,
                query_rewritten=False,
            )

        evidence = (
            self.evidence_selector.select(
                question=question,
                passages=candidates,
            )
        )

        request_type = evidence[
            "request_type"
        ]

        if (
            request_type
            == "personalized_medical_decision"
        ):
            return self._medical_decision_response(
                reason=evidence["reason"],
                candidates=candidates,
                retrieval_query=question,
            )

        if request_type == "out_of_scope":
            return self._out_of_scope_response(
                reason=evidence["reason"],
                candidates=candidates,
                retrieval_query=question,
            )

        retrieval_query = question
        query_rewritten = False

        if not evidence["sufficient"]:
            rewritten_query = (
                self.query_rewriter.rewrite(
                    question=question,
                    medicine_name=medicine_name,
                )
            )

            if (
                self._normalize_text(
                    rewritten_query
                )
                != self._normalize_text(
                    question
                )
            ):
                rewritten_candidates = (
                    self._retrieve(
                        query=rewritten_query,
                        cis=cis,
                    )
                )

                if rewritten_candidates:
                    rewritten_evidence = (
                        self.evidence_selector.select(
                            question=question,
                            passages=rewritten_candidates,
                        )
                    )

                    rewritten_type = (
                        rewritten_evidence[
                            "request_type"
                        ]
                    )

                    if (
                        rewritten_type
                        == "personalized_medical_decision"
                    ):
                        return (
                            self._medical_decision_response(
                                reason=(
                                    rewritten_evidence[
                                        "reason"
                                    ]
                                ),
                                candidates=(
                                    rewritten_candidates
                                ),
                                retrieval_query=(
                                    rewritten_query
                                ),
                            )
                        )

                    if (
                        rewritten_type
                        == "out_of_scope"
                    ):
                        return (
                            self._out_of_scope_response(
                                reason=(
                                    rewritten_evidence[
                                        "reason"
                                    ]
                                ),
                                candidates=(
                                    rewritten_candidates
                                ),
                                retrieval_query=(
                                    rewritten_query
                                ),
                            )
                        )

                    candidates = (
                        rewritten_candidates
                    )

                    evidence = (
                        rewritten_evidence
                    )

                    retrieval_query = (
                        rewritten_query
                    )

                    query_rewritten = True

        if not evidence["sufficient"]:
            return self._insufficient_response(
                reason=evidence["reason"],
                candidates=candidates,
                retrieval_query=retrieval_query,
                query_rewritten=query_rewritten,
            )

        selected_passages = (
            evidence["passages"]
        )

        source_passages = [
            (
                f"S{index}",
                passage,
            )
            for index, passage
            in enumerate(
                selected_passages,
                start=1,
            )
        ]

        answer = self.generator.generate(
            question=question,
            medicine_name=medicine_name,
            source_passages=source_passages,
        )

        answer = self._normalize_answer(
            answer
        )

        citations = (
            self._extract_citations(
                answer
            )
        )

        valid_source_ids = {
            source_id
            for source_id, _
            in source_passages
        }

        invalid_citations = [
            citation
            for citation in citations
            if citation
            not in valid_source_ids
        ]

        valid_citations = [
            citation
            for citation in citations
            if citation
            in valid_source_ids
        ]

        if (
            invalid_citations
            or not valid_citations
        ):
            return (
                self._grounding_failed_response(
                    selected_passages=(
                        selected_passages
                    ),
                    candidates=candidates,
                    reason=evidence["reason"],
                    invalid_citations=(
                        invalid_citations
                    ),
                    retrieval_query=(
                        retrieval_query
                    ),
                    query_rewritten=(
                        query_rewritten
                    ),
                )
            )

        source_lookup = dict(
            source_passages
        )

        used_sources = []
        seen_references = set()

        for citation in valid_citations:
            if citation in seen_references:
                continue

            seen_references.add(
                citation
            )

            passage = source_lookup[
                citation
            ]

            used_sources.append(
                {
                    "reference": citation,
                    "document_type": passage[
                        "document_type"
                    ],
                    "section_number": passage[
                        "section_number"
                    ],
                    "section_title": passage[
                        "section_title"
                    ],
                    "source": passage[
                        "source"
                    ],
                    "source_url": passage[
                        "source_url"
                    ],
                }
            )

        return {
            "status": "answered",
            "answer": answer,
            "sources": used_sources,
            "passages": selected_passages,
            "candidates": candidates,
            "evidence_reason": (
                evidence["reason"]
            ),
            "invalid_citations": [],
            "retrieval_query": (
                retrieval_query
            ),
            "query_rewritten": (
                query_rewritten
            ),
            "request_type": "informational",
        }

    def _retrieve(
        self,
        query: str,
        cis: str,
    ) -> list[dict]:
        return self.retriever.search(
            question=query,
            cis=cis,
            document_type="RCP",
            top_k=RETRIEVAL_CANDIDATE_K,
        )

    def _normalize_text(
        self,
        value: str,
    ) -> str:
        value = unicodedata.normalize(
            "NFKC",
            value,
        )

        return " ".join(
            value.casefold().split()
        )

    def _medical_decision_response(
        self,
        reason: str,
        candidates: list[dict],
        retrieval_query: str,
    ) -> dict:
        return {
            "status": "medical_decision_blocked",
            "answer": (
                "Je peux expliquer les informations "
                "pharmaceutiques disponibles sur ce médicament, "
                "mais je ne peux pas décider si vous devez le "
                "prendre, l'arrêter ou modifier votre traitement. "
                "Pour une décision adaptée à votre situation, "
                "consultez un professionnel de santé."
            ),
            "sources": [],
            "passages": [],
            "candidates": candidates,
            "evidence_reason": reason,
            "invalid_citations": [],
            "retrieval_query": retrieval_query,
            "query_rewritten": False,
            "request_type": (
                "personalized_medical_decision"
            ),
        }

    def _out_of_scope_response(
        self,
        reason: str,
        candidates: list[dict],
        retrieval_query: str,
    ) -> dict:
        return {
            "status": "out_of_scope",
            "answer": (
                "Cette demande ne relève pas des "
                "informations pharmaceutiques que "
                "Pharmora fournit sur le médicament "
                "sélectionné."
            ),
            "sources": [],
            "passages": [],
            "candidates": candidates,
            "evidence_reason": reason,
            "invalid_citations": [],
            "retrieval_query": retrieval_query,
            "query_rewritten": False,
            "request_type": "out_of_scope",
        }

    def _insufficient_response(
        self,
        reason: str,
        candidates: list[dict],
        retrieval_query: str,
        query_rewritten: bool,
    ) -> dict:
        return {
            "status": "insufficient_evidence",
            "answer": (
                "Les sources pharmaceutiques disponibles "
                "ne contiennent pas suffisamment "
                "d'informations pour répondre de manière "
                "fiable à cette question."
            ),
            "sources": [],
            "passages": [],
            "candidates": candidates,
            "evidence_reason": reason,
            "invalid_citations": [],
            "retrieval_query": retrieval_query,
            "query_rewritten": query_rewritten,
            "request_type": "informational",
        }

    def _grounding_failed_response(
        self,
        selected_passages: list[dict],
        candidates: list[dict],
        reason: str,
        invalid_citations: list[str],
        retrieval_query: str,
        query_rewritten: bool,
    ) -> dict:
        return {
            "status": "grounding_failed",
            "answer": (
                "Je ne peux pas fournir une réponse "
                "suffisamment sourcée à partir des "
                "informations disponibles."
            ),
            "sources": [],
            "passages": selected_passages,
            "candidates": candidates,
            "evidence_reason": reason,
            "invalid_citations": (
                invalid_citations
            ),
            "retrieval_query": retrieval_query,
            "query_rewritten": query_rewritten,
            "request_type": "informational",
        }

    def _normalize_answer(
        self,
        answer: str,
    ) -> str:
        answer = unicodedata.normalize(
            "NFKC",
            answer,
        )

        for character in (
            "\u200b",
            "\u200c",
            "\u200d",
            "\ufeff",
        ):
            answer = answer.replace(
                character,
                "",
            )

        answer = re.sub(
            r"【\s*S(\d+)\s*】",
            r"[S\1]",
            answer,
            flags=re.IGNORECASE,
        )

        answer = re.sub(
            r"\[\s*S(\d+)\s*\]",
            r"[S\1]",
            answer,
            flags=re.IGNORECASE,
        )

        return answer.strip()

    def _extract_citations(
        self,
        answer: str,
    ) -> list[str]:
        matches = re.findall(
            r"\[S(\d+)\]",
            answer,
            flags=re.IGNORECASE,
        )

        citations = []

        for number in matches:
            reference = f"S{number}"

            if reference not in citations:
                citations.append(
                    reference
                )

        return citations