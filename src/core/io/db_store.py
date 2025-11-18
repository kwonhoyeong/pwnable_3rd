"""Database persistence manager for pipeline results."""

from typing import Any, Dict, List, Optional

from analyzer.app.repository import AnalysisRepository
from cvss_fetcher.app.repository import CVSSRepository
from epss_fetcher.app.repository import EPSSRepository
from mapping_collector.app.repository import MappingRepository
from threat_agent.app.repository import ThreatRepository

from src.core.logger import get_logger
from src.core.utils.timestamps import ensure_datetime

logger = get_logger(__name__)


class PersistenceManager:
    """Manages database persistence for pipeline results."""

    def __init__(self, session: Optional[Any] = None):
        """
        Initialize persistence manager.

        Args:
            session: SQLAlchemy async session (if None, persistence is disabled)
        """
        self.session = session
        self._mapping_repo = MappingRepository(session) if session else None
        self._epss_repo = EPSSRepository(session) if session else None
        self._cvss_repo = CVSSRepository(session) if session else None
        self._threat_repo = ThreatRepository(session) if session else None
        self._analysis_repo = AnalysisRepository(session) if session else None

    async def persist_mappings(
        self, package: str, version_range: str, cve_ids: List[str]
    ) -> bool:
        """
        Persist CVE mappings to database.

        Args:
            package: Package name
            version_range: Version range
            cve_ids: List of CVE IDs

        Returns:
            True if successful, False if persistence disabled or failed
        """
        if not self.session or not self._mapping_repo:
            return False

        try:
            await self._mapping_repo.upsert_mapping(package, version_range, cve_ids)
            await self.session.commit()
            logger.debug("Persisted mappings for %s@%s (%d CVEs)", package, version_range, len(cve_ids))
            return True
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to persist mappings to DB: %s", exc)
            return False

    async def persist_epss_scores(
        self, cve_results: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Persist EPSS scores to database.

        Args:
            cve_results: Dict mapping CVE ID to EPSS record

        Returns:
            True if successful, False if persistence disabled or failed
        """
        if not self.session or not self._epss_repo:
            return False

        try:
            for cve_id, record in cve_results.items():
                score = record.get("epss_score", 0.0)
                # Only persist if we have a valid score
                if score is not None:
                    await self._epss_repo.upsert_score(
                        cve_id,
                        float(score),
                        ensure_datetime(record.get("collected_at")),
                    )
            await self.session.commit()
            logger.debug("Persisted EPSS scores for %d CVEs", len(cve_results))
            return True
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to persist EPSS to DB: %s", exc)
            return False

    async def persist_cvss_scores(
        self, cve_results: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Persist CVSS scores to database.

        Args:
            cve_results: Dict mapping CVE ID to CVSS record

        Returns:
            True if successful, False if persistence disabled or failed
        """
        if not self.session or not self._cvss_repo:
            return False

        try:
            for cve_id, record in cve_results.items():
                score = record.get("cvss_score", 0.0)
                # Only persist if we have a valid score
                if score is not None:
                    await self._cvss_repo.upsert_score(
                        cve_id,
                        float(score),
                        record.get("vector"),
                        ensure_datetime(record.get("collected_at")),
                    )
            await self.session.commit()
            logger.debug("Persisted CVSS scores for %d CVEs", len(cve_results))
            return True
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to persist CVSS to DB: %s", exc)
            return False

    async def persist_threat_cases(
        self, cve_id: str, package: str, version_range: str, cases: List[Dict[str, Any]]
    ) -> bool:
        """
        Persist threat cases to database.

        Args:
            cve_id: CVE identifier
            package: Package name
            version_range: Version range
            cases: List of serialized threat cases

        Returns:
            True if successful, False if persistence disabled or failed
        """
        if not self.session or not self._threat_repo:
            return False

        try:
            await self._threat_repo.upsert_cases(cve_id, package, version_range, cases)
            logger.debug("Persisted threat cases for %s", cve_id)
            return True
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to persist threat cases to DB: %s", exc)
            return False

    async def persist_analysis(
        self,
        cve_id: str,
        risk_level: str,
        recommendations: List[str],
        analysis_summary: str,
        generated_at: Any,
    ) -> bool:
        """
        Persist analysis results to database.

        Args:
            cve_id: CVE identifier
            risk_level: Risk level (Low/Medium/High)
            recommendations: List of recommendations
            analysis_summary: Summary text
            generated_at: Timestamp when analysis was generated

        Returns:
            True if successful, False if persistence disabled or failed
        """
        if not self.session or not self._analysis_repo:
            return False

        try:
            await self._analysis_repo.upsert_analysis(
                cve_id=cve_id,
                risk_level=risk_level,
                recommendations=recommendations,
                analysis_summary=analysis_summary,
                generated_at=ensure_datetime(generated_at),
            )
            await self.session.commit()
            logger.debug("Persisted analysis for %s (risk=%s)", cve_id, risk_level)
            return True
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to persist analysis to DB: %s", exc)
            return False
