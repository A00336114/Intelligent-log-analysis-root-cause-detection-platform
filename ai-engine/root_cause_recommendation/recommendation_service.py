import logging
import os
from typing import Any

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from data_processing.anomaly_repository import AnomalyRepository


logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self) -> None:
        self.repository = AnomalyRepository()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    def find_similar_incidents(self, incident_id: int, limit: int = 5) -> list[dict[str, Any]]:
        current = self.repository.fetch_incident_with_parsed_log(incident_id)
        if current is None:
            return []

        candidates = self.repository.fetch_incidents_for_similarity(exclude_incident_id=incident_id)
        candidates = [candidate for candidate in candidates if self._has_signal(candidate)]
        if not candidates:
            return []

        corpus = [self._incident_text(current)] + [self._incident_text(candidate) for candidate in candidates]
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=1200).fit_transform(corpus)
        scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()

        ranked = []
        for candidate, score in zip(candidates, scores):
            bonus = self._structured_match_bonus(current, candidate)
            final_score = min(1.0, float(score) + bonus)
            ranked.append({
                "incident_id": candidate["id"],
                "incident_number": candidate.get("incidentNumber"),
                "alert_name": candidate.get("alertName"),
                "service_name": candidate.get("serviceName"),
                "status": candidate.get("status"),
                "severity": candidate.get("severity"),
                "similarity_score": round(final_score, 4),
                "notes": candidate.get("notes"),
                "raw_log": candidate.get("rawLog"),
                "parsed_log": candidate.get("parsedLog"),
            })

        ranked.sort(key=lambda item: item["similarity_score"], reverse=True)
        return ranked[:limit]

    def generate_recommendation(self, incident_id: int) -> dict[str, Any]:
        current = self.repository.fetch_incident_with_parsed_log(incident_id)
        if current is None:
            raise ValueError(f"Incident {incident_id} was not found")

        similar = self.find_similar_incidents(incident_id, limit=3)
        best_match = similar[0] if similar else None

        root_cause, fix, model_used = self._generate_with_ollama(current, similar)
        if not root_cause or not fix:
            root_cause, fix = self._rule_based_recommendation(current, best_match)
            model_used = "rules-and-similarity"

        evidence = self._build_evidence(current, similar)
        saved = self.repository.save_recommendation(
            incident_id=incident_id,
            similar_incident_id=best_match["incident_id"] if best_match else None,
            similarity_score=best_match["similarity_score"] if best_match else 0.0,
            recommended_root_cause=root_cause,
            recommended_fix=fix,
            evidence=evidence,
            model_used=model_used,
        )

        saved["similar_incidents"] = similar
        return saved

    def get_recommendation(self, incident_id: int) -> dict[str, Any] | None:
        recommendation = self.repository.fetch_recommendation_by_incident_id(incident_id)
        if recommendation:
            recommendation["similar_incidents"] = self.find_similar_incidents(incident_id, limit=3)
        return recommendation

    def get_recommendations(self) -> list[dict[str, Any]]:
        recommendations = self.repository.fetch_recommendations()
        for recommendation in recommendations:
            recommendation["similar_incidents"] = self.find_similar_incidents(
                recommendation["incident_id"],
                limit=3,
            )
        return recommendations

    def _has_signal(self, incident: dict[str, Any]) -> bool:
        values = [
            incident.get("alertName"),
            incident.get("serviceName"),
            incident.get("severity"),
            incident.get("status"),
            incident.get("rawLog"),
            incident.get("notes"),
        ]
        parsed_log = incident.get("parsedLog") or {}
        values.extend([
            parsed_log.get("failureType"),
            parsed_log.get("exceptionType"),
            parsed_log.get("errorMessage"),
        ])
        return any(str(value or "").strip() for value in values)

    def _incident_text(self, incident: dict[str, Any]) -> str:
        parsed_log = incident.get("parsedLog") or {}
        fields = [
            incident.get("alertName"),
            incident.get("title"),
            incident.get("description"),
            incident.get("serviceName"),
            incident.get("severity"),
            incident.get("source"),
            incident.get("status"),
            incident.get("rawLog"),
            incident.get("notes"),
            parsed_log.get("logLevel"),
            parsed_log.get("errorMessage"),
            parsed_log.get("exceptionType"),
            parsed_log.get("statusCode"),
            parsed_log.get("failureType"),
        ]
        return " ".join(str(value) for value in fields if value)

    def _structured_match_bonus(self, current: dict[str, Any], candidate: dict[str, Any]) -> float:
        bonus = 0.0
        current_parsed = current.get("parsedLog") or {}
        candidate_parsed = candidate.get("parsedLog") or {}
        if current.get("serviceName") and current.get("serviceName") == candidate.get("serviceName"):
            bonus += 0.15
        if current.get("alertName") and current.get("alertName") == candidate.get("alertName"):
            bonus += 0.12
        if current_parsed.get("failureType") and current_parsed.get("failureType") == candidate_parsed.get("failureType"):
            bonus += 0.12
        if current_parsed.get("exceptionType") and current_parsed.get("exceptionType") == candidate_parsed.get("exceptionType"):
            bonus += 0.08
        if current_parsed.get("statusCode") and current_parsed.get("statusCode") == candidate_parsed.get("statusCode"):
            bonus += 0.06
        if str(candidate.get("status") or "").upper() == "RESOLVED" and candidate.get("notes"):
            bonus += 0.08
        return bonus

    def _generate_with_ollama(
        self,
        current: dict[str, Any],
        similar: list[dict[str, Any]],
    ) -> tuple[str | None, str | None, str]:
        prompt = self._build_prompt(current, similar)
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=8,
            )
            response.raise_for_status()
            text = str(response.json().get("response") or "").strip()
            if not text:
                return None, None, self.ollama_model

            root_cause = self._extract_section(text, "Root cause")
            fix = self._extract_section(text, "Recommended fix")
            return root_cause or None, fix or text, self.ollama_model
        except Exception as error:
            logger.info("Ollama recommendation skipped: %s", error)
            return None, None, "rules-and-similarity"

    def _build_prompt(self, current: dict[str, Any], similar: list[dict[str, Any]]) -> str:
        similar_notes = "\n\n".join(
            [
                f"Incident {item.get('incident_number') or item['incident_id']} "
                f"score={item['similarity_score']}\nNotes:\n{item.get('notes') or 'No notes available'}"
                for item in similar
            ]
        )
        return (
            "You are helping an incident analyst. Use the current incident and similar past notes. "
            "Return two short sections exactly named 'Root cause:' and 'Recommended fix:'.\n\n"
            f"Current incident:\n{self._incident_text(current)}\n\n"
            f"Similar past incidents:\n{similar_notes or 'No similar incidents found.'}"
        )

    def _extract_section(self, text: str, heading: str) -> str:
        marker = f"{heading}:"
        start = text.lower().find(marker.lower())
        if start < 0:
            return ""

        value = text[start + len(marker):].strip()
        for next_heading in ["Root cause:", "Recommended fix:"]:
            index = value.lower().find(next_heading.lower())
            if index > 0:
                value = value[:index].strip()
        return value.strip("- \n")

    def _rule_based_recommendation(
        self,
        current: dict[str, Any],
        best_match: dict[str, Any] | None,
    ) -> tuple[str, str]:
        parsed_log = current.get("parsedLog") or {}
        service = current.get("serviceName") or parsed_log.get("serviceName") or "affected service"
        failure_type = str(parsed_log.get("failureType") or "").upper()
        status_code = parsed_log.get("statusCode")
        notes = best_match.get("notes") if best_match else None

        if notes:
            return (
                f"The incident is similar to a previous {service} incident. The past notes indicate the same operational pattern.",
                self._extract_resolution_from_notes(notes),
            )

        if "PAYMENT" in service.upper() or "PAYMENT" in failure_type:
            return (
                "The payment flow is failing or blocking requests, likely due to payment-service or a downstream payment dependency.",
                "Check payment-service logs, restart it with 'docker compose up -d payment-service' if it is stopped, then verify the health endpoint and Grafana alert state.",
            )
        if status_code == 401 or "AUTH" in failure_type:
            return (
                "Authentication failures are being detected from application logs.",
                "Check the failed login source, confirm whether it is test traffic, then stop the generator or fix credentials before resolving the incident.",
            )
        if status_code and int(status_code) >= 500:
            return (
                f"{service} is returning server-side errors.",
                f"Inspect {service} logs, restart the container if unhealthy, verify dependencies, and confirm that 5xx errors stop.",
            )
        return (
            f"{service} is showing an incident pattern that needs service and log review.",
            f"Check container status for {service}, inspect the raw log and parsed log fields, then restart or fix the failing dependency before marking resolved.",
        )

    def _extract_resolution_from_notes(self, notes: str) -> str:
        lower = notes.lower()
        marker = "resolution steps:"
        index = lower.find(marker)
        if index >= 0:
            value = notes[index + len(marker):].strip()
            verification_index = value.lower().find("verification:")
            if verification_index >= 0:
                value = value[:verification_index].strip()
            return value
        return notes.strip()

    def _build_evidence(self, current: dict[str, Any], similar: list[dict[str, Any]]) -> str:
        parsed_log = current.get("parsedLog") or {}
        best = similar[0] if similar else None
        lines = [
            f"Current service: {current.get('serviceName') or 'unknown'}",
            f"Alert: {current.get('alertName') or 'unknown'}",
            f"Failure type: {parsed_log.get('failureType') or 'unknown'}",
            f"Status code: {parsed_log.get('statusCode') or 'unknown'}",
        ]
        if best:
            lines.append(
                f"Best match: {best.get('incident_number') or best['incident_id']} "
                f"with score {best['similarity_score']}"
            )
        else:
            lines.append("No similar incident with usable notes was found.")
        return "\n".join(lines)
