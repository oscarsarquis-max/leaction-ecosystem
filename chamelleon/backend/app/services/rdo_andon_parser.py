"""Triagem Andon Digital — detecta anomalias críticas em payloads de RDO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EQUIPMENT_BROKEN_STATUS = "parado por quebra"
OCCURRENCE_ACCIDENT_TYPE = "acidente"
WORKFORCE_ABSENCE_ROW_THRESHOLD = 3
WORKFORCE_ABSENCE_TOTAL_THRESHOLD = 5


@dataclass(frozen=True)
class AndonAnomaly:
    anomaly_type: str
    title: str
    description: str


class RdoAndonParser:
    """Analisa o RDO e retorna anomalias que exigem ticket Kaizen em estágio Alerta."""

    def detect_anomalies(self, payload: dict[str, Any]) -> list[AndonAnomaly]:
        rdo = self._extract_rdo_body(payload)
        anomalies: list[AndonAnomaly] = []

        anomalies.extend(self._scan_equipment_breakdowns(rdo))
        anomalies.extend(self._scan_accidents(rdo))
        anomalies.extend(self._scan_excessive_absences(rdo))

        if not rdo.get("ppe_compliant", True) and rdo.get("ppe_compliant") is False:
            detail = (rdo.get("ppe_compliant_details") or "").strip()
            anomalies.append(
                AndonAnomaly(
                    anomaly_type="ppe_non_compliance",
                    title="Alerta Crítico: Não conformidade de EPI",
                    description=detail or "RDO registrou não conformidade de EPI no canteiro.",
                )
            )

        if rdo.get("delay_waiting_material"):
            anomalies.append(
                AndonAnomaly(
                    anomaly_type="delay_material",
                    title="Alerta: Equipe parada esperando material",
                    description="O encarregado registrou espera por material no turno.",
                )
            )
        if rdo.get("delay_rework"):
            anomalies.append(
                AndonAnomaly(
                    anomaly_type="delay_rework",
                    title="Alerta: Retrabalho no canteiro",
                    description="Foi necessário refazer serviço hoje.",
                )
            )
        if rdo.get("delay_lack_of_front"):
            anomalies.append(
                AndonAnomaly(
                    anomaly_type="delay_front",
                    title="Alerta: Falta de frente de trabalho",
                    description="A equipe ficou sem frente de trabalho disponível.",
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
                AndonAnomaly(
                    anomaly_type="equipment_breakdown",
                    title=f"Alerta Crítico: {name} Parada por Quebra",
                    description=description,
                )
            )
        return anomalies

    def _scan_accidents(self, rdo: dict[str, Any]) -> list[AndonAnomaly]:
        anomalies: list[AndonAnomaly] = []
        for item in rdo.get("occurrences") or []:
            if not isinstance(item, dict):
                continue
            occ_type = str(item.get("type") or "").strip().lower()
            if occ_type != OCCURRENCE_ACCIDENT_TYPE:
                continue
            description = (
                (item.get("what_happened") or item.get("description") or "").strip()
                or "Acidente registrado no RDO."
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
            anomalies.append(
                AndonAnomaly(
                    anomaly_type="accident",
                    title="Alerta Crítico: Acidente de Trabalho",
                    description=description,
                )
            )
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
                AndonAnomaly(
                    anomaly_type="excessive_absences",
                    title="Alerta Crítico: Faltas Excessivas no Efetivo",
                    description=" | ".join(description_parts),
                )
            )
        return anomalies
