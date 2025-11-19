"""데이터 모델 정의(Data model definitions)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class PackageInput(BaseModel):
    """패키지 입력 모델(Package input model)."""

    package: str = Field(..., description="패키지 이름(Package name)")
    version_range: str = Field(..., description="버전 범위(Version range)")
    ecosystem: str = Field(default="npm", description="패키지 생태계(Ecosystem)")
    collected_at: datetime = Field(..., description="수집 시각(Collection timestamp)")


class PackageMapping(BaseModel):
    """패키지와 CVE 매핑 모델(Package to CVE mapping model)."""

    package: str
    version_range: str
    ecosystem: str = "npm"
    cve_ids: List[str]
    collected_at: datetime
