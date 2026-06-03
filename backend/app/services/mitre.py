from dataclasses import dataclass
from enum import StrEnum


class FindingType(StrEnum):
    vulnerability = "vulnerability"
    exposure = "exposure"
    misconfiguration = "misconfiguration"
    weak_auth = "weak_auth"
    informational = "informational"


@dataclass(frozen=True)
class MitreMapping:
    tactic: str
    technique_id: str
    technique_name: str
    confidence: float
    evidence: str


class MitreAttackMapper:
    def map_finding(
        self,
        finding_type: FindingType,
        service_name: str | None,
        title: str,
    ) -> tuple[MitreMapping, ...]:
        normalized_service = (service_name or "").lower()
        normalized_title = title.lower()
        mappings: list[MitreMapping] = []

        if normalized_service in {"smb", "microsoft-ds", "netbios-ssn"}:
            mappings.append(
                MitreMapping(
                    tactic="Lateral Movement",
                    technique_id="T1021.002",
                    technique_name="SMB/Windows Admin Shares",
                    confidence=0.72,
                    evidence="SMB exposure can support lateral movement analysis when trust context exists.",
                )
            )

        if finding_type == FindingType.weak_auth or "weak authentication" in normalized_title:
            mappings.append(
                MitreMapping(
                    tactic="Credential Access",
                    technique_id="T1110",
                    technique_name="Brute Force",
                    confidence=0.68,
                    evidence="Weak authentication finding indicates credential-access risk.",
                )
            )

        if normalized_service in {"ssh", "rdp", "ms-wbt-server"}:
            mappings.append(
                MitreMapping(
                    tactic="Lateral Movement",
                    technique_id="T1021",
                    technique_name="Remote Services",
                    confidence=0.64,
                    evidence="Remote administration service is exposed and should be reviewed defensively.",
                )
            )

        return tuple(mappings)

