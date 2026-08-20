"""Triagem Andon Digital — detecta anomalias críticas em payloads de RDO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.kaizen_models import (
    RESTRICTION_EQUIPAMENTO,
    RESTRICTION_FRENTE_DE_TRABALHO,
    RESTRICTION_MAO_DE_OBRA,
    RESTRICTION_MATERIAL,
    SEVERITY_ALTA,
    SEVERITY_BAIXA,
    SEVERITY_CRITICA,
    SEVERITY_MEDIA,
)

EQUIPMENT_BROKEN_STATUS = "parado por quebra"
OCCURRENCE_ACCIDENT_TYPE = "acidente"

OCCURRENCE_ANDON_LABELS: dict[str, tuple[str, str]] = {
    "acidente": ("accident", "Alerta Crítico: Acidente de Trabalho"),
    "falta_material": ("material_shortage", "Alerta: Falta de material"),
    "queda_energia": ("power_outage", "Alerta: Queda de energia"),
    "chuva_forte": ("heavy_rain", "Alerta: Chuva forte no canteiro"),
    "geral": ("general_occurrence", "Alerta: Ocorrência no canteiro"),
}
WORKFORCE_ABSENCE_ROW_THRESHOLD = 3
WORKFORCE_ABSENCE_TOTAL_THRESHOLD = 5

ANOMALY_TYPE_TO_RESTRICTION_CATEGORY: dict[str, str] = {
    "equipment_breakdown": RESTRICTION_EQUIPAMENTO,
    "delay_material": RESTRICTION_MATERIAL,
    "material_shortage": RESTRICTION_MATERIAL,
    "excessive_absences": RESTRICTION_MAO_DE_OBRA,
    "delay_front": RESTRICTION_FRENTE_DE_TRABALHO,
}

ANDON_SEVERITY: dict[str, str] = {
    "accident": SEVERITY_CRITICA,
    "ppe_non_compliance": SEVERITY_CRITICA,
    "equipment_breakdown": SEVERITY_ALTA,
    "excessive_absences": SEVERITY_ALTA,
    "delay_material": SEVERITY_MEDIA,
    "delay_rework": SEVERITY_MEDIA,
    "delay_front": SEVERITY_MEDIA,
    "power_outage": SEVERITY_MEDIA,
    "material_shortage": SEVERITY_BAIXA,
    "heavy_rain": SEVERITY_BAIXA,
    "general_occurrence": SEVERITY_BAIXA,
    "occurrence": SEVERITY_BAIXA,
}


@dataclass(frozen=True)
class AndonAnomaly:
    anomaly_type: str
    title: str
    description: str
    severity: str = SEVERITY_MEDIA
    category: str | None = None


def _anomaly(anomaly_type: str, title: str, description: str) -> AndonAnomaly:
    return AndonAnomaly(
        anomaly_type=anomaly_type,
        title=title,
        description=description,
        severity=ANDON_SEVERITY.get(anomaly_type, SEVERITY_MEDIA),
        category=ANOMALY_TYPE_TO_RESTRICTION_CATEGORY.get(anomaly_type),
    )


class RdoAndonParser:
    """Analisa o RDO e retorna anomalias (restrição de planejamento ou alerta Kaizen)."""

    def detect_anomalies(self, payload: dict[str, Any]) -> list[AndonAnomaly]:
        rdo = self._extract_rdo_body(payload)
        anomalies: list[AndonAnomaly] = []

        anomalies.extend(self._scan_equipment_breakdowns(rdo))
        anomalies.extend(self._scan_accidents(rdo))
        anomalies.extend(self._scan_occurrences(rdo))
        anomalies.extend(self._scan_excessive_absences(rdo))

        if not rdo.get("ppe_compliant", True) and rdo.get("ppe_compliant") is False:
            detail = (rdo.get("ppe_compliant_details") or "").strip()
            anomalies.append(
                _anomaly(
                    "ppe_non_compliance",
                    "Alerta Crítico: Não conformidade de EPI",
                    detail or "RDO registrou não conformidade de EPI no canteiro.",
                )
            )

        if rdo.get("delay_waiting_material"):
            # quantity==0 = sem recebimento registrado hoje (não prova falta de estoque).
            # Só enriquece a descrição; o disparo continua sendo delay_waiting_material.
            zero_supplies = [
                str(item.get("label") or item.get("key") or "").strip()
                for item in (rdo.get("supplies") or [])
                if isinstance(item, dict) and (item.get("quantity") or 0) == 0
            ]
            zero_supplies = [s for s in zero_supplies if s]
            description = "O encarregado registrou espera por material no turno."
            if zero_supplies:
                description += f" Sem recebimento hoje de: {', '.join(zero_supplies)}."
            anomalies.append(
                _anomaly(
                    "delay_material",
                    "Alerta: Equipe parada esperando material",
                    description,
                )
            )
        if rdo.get("delay_rework"):
            anomalies.append(
                _anomaly(
                    "delay_rework",
                    "Alerta: Retrabalho no canteiro",
                    "Foi necessário refazer serviço hoje.",
                )
            )
        if rdo.get("delay_lack_of_front"):
            anomalies.append(
                _anomaly(
                    "delay_front",
                    "Alerta: Falta de frente de trabalho",
                    "A equipe ficou sem frente de trabalho disponível.",
                )
            )

        return anomalies

    @staticmethod
    def _extract_rdo_body(payload: dict[str, Any]) -> dict[str, Any]:
        nested = payload.get("rdo")
        if isinstance(nested, dict):
            return nested
        if any(
            key in payload
            for key in ("equipment_statuses", "occurrences", "workforce", "ppe_compliant")
        ):
            return payload
        return payload

    def _scan_equipment_breakdowns(self, rdo: dict[str, Any]) -> list[AndonAnomaly]:
        anomalies: list[AndonAnomaly] = []
        for item in rdo.get("equipment_statuses") or []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").strip().lower()
            if status != EQUIPMENT_BROKEN_STATUS:
                continue
            name = str(item.get("equipment_name") or "Equipamento").strip()
            qty = int(item.get("quantity") or 0)
            remarks = (item.get("remarks") or "").strip()
            qty_text = f" ({qty} un.)" if qty > 1 else ""
            description = remarks or f"Equipamento reportado como parado por quebra no RDO.{qty_text}"
            anomalies.append(
                _anomaly(
                    "equipment_breakdown",
                    f"Alerta Crítico: {name} Parada por Quebra",
                    description,
                )
            )
        return anomalies

    def _scan_accidents(self, rdo: dict[str, Any]) -> list[AndonAnomaly]:
        return self._scan_occurrences(rdo, only_type=OCCURRENCE_ACCIDENT_TYPE)

    def _scan_occurrences(
        self, rdo: dict[str, Any], *, only_type: str | None = None
    ) -> list[AndonAnomaly]:
        anomalies: list[AndonAnomaly] = []
        for item in rdo.get("occurrences") or []:
            if not isinstance(item, dict):
                continue
            occ_type = str(item.get("type") or "").strip().lower()
            if only_type and occ_type != only_type:
                continue
            if not only_type and occ_type == OCCURRENCE_ACCIDENT_TYPE:
                # Acidente já tratado em _scan_accidents para manter título crítico dedicado.
                continue
            label = OCCURRENCE_ANDON_LABELS.get(occ_type)
            if not label and only_type:
                continue
            anomaly_type, title = label or ("occurrence", "Alerta: Ocorrência no canteiro")
            description = (
                (item.get("what_happened") or item.get("description") or "").strip()
                or "Ocorrência registrada no RDO."
            )
            location = (item.get("exact_location") or "").strip()
            containment = (item.get("immediate_action_taken") or "").strip()
            if location:
                description = f"Local: {location} | {description}"
            if containment:
                description = f"{description} | Ação na hora: {containment}"
            safety = (item.get("safety_ppe_notes") or "").strip()
            if safety:
                description = f"{description} | EPI/Segurança: {safety}"
            anomalies.append(_anomaly(anomaly_type, title, description))
        return anomalies

    def _scan_excessive_absences(self, rdo: dict[str, Any]) -> list[AndonAnomaly]:
        anomalies: list[AndonAnomaly] = []
        workforce = [row for row in (rdo.get("workforce") or []) if isinstance(row, dict)]
        if not workforce:
            return anomalies

        total_absences = 0
        hot_spots: list[str] = []

        for row in workforce:
            absences = int(
                row.get("absences_count")
                if row.get("absences_count") is not None
                else row.get("absences") or 0
            )
            total_absences += absences
            if absences >= WORKFORCE_ABSENCE_ROW_THRESHOLD:
                role = str(row.get("role") or "Função").strip()
                detail = (row.get("absences_details") or "").strip()
                hot_spots.append(f"{role}: {absences} falta(s)" + (f" — {detail}" if detail else ""))

        if total_absences >= WORKFORCE_ABSENCE_TOTAL_THRESHOLD or hot_spots:
            description_parts = hot_spots or [
                f"Total de faltas no efetivo: {total_absences} (limite {WORKFORCE_ABSENCE_TOTAL_THRESHOLD})."
            ]
            anomalies.append(
                _anomaly(
                    "excessive_absences",
                    "Alerta Crítico: Faltas Excessivas no Efetivo",
                    " | ".join(description_parts),
                )
            )
        return anomalies
