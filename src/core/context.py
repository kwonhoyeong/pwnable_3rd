"""Pipeline execution context for sharing state across agents.

This module provides a context object to track pipeline state, including
package information, caching flags, and execution progress.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from mapping_collector.app.models import PackageInput


@dataclass
class PipelineContext:
    """
    Shared execution context for the CVE analysis pipeline.

    Tracks package information, configuration flags, and intermediate results
    to avoid repeating work and to provide consistent metadata across agents.
    """

    # Package information
    package_payload: PackageInput

    # Configuration flags
    skip_threat_agent: bool = False
    force_refresh: bool = False

    # Execution metadata
    started_at: datetime = field(default_factory=datetime.utcnow)

    # Intermediate results (populated during pipeline execution)
    cve_ids: List[str] = field(default_factory=list)
    epss_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cvss_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    threat_results: Dict[str, Any] = field(default_factory=dict)
    analysis_results: Dict[str, Any] = field(default_factory=dict)

    # Errors encountered during execution (for diagnostics)
    errors: List[str] = field(default_factory=list)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since pipeline started."""
        return (datetime.utcnow() - self.started_at).total_seconds()

    def add_error(self, step: str, message: str) -> None:
        """Record an error encountered during pipeline execution."""
        error_msg = f"[{step}] {message}"
        self.errors.append(error_msg)

    def summary(self) -> Dict[str, Any]:
        """Get a summary of pipeline execution context."""
        return {
            "package": self.package_payload.package,
            "version": self.package_payload.version_range,
            "cve_count": len(self.cve_ids),
            "skip_threat_agent": self.skip_threat_agent,
            "force_refresh": self.force_refresh,
            "elapsed_seconds": self.elapsed_seconds,
            "error_count": len(self.errors),
        }
