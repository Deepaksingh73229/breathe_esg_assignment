"""
Base parser interface.

All source-specific parsers (SAP, Utility, Travel) inherit from BaseParser and implement:
  - validate_file()  → quick structural check before committing to full parse
  - parse_rows()     → yields one ParseResult per logical source row

This abstraction lets us add new source types (e.g., Oracle ERP, Workday)
without touching the pipeline orchestrator (ingestion/services.py).
"""
from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, List, Optional


class ParseResult:
    """
    Structured result from parsing a single row / segment.

    status:
      "valid"      — parsed cleanly, create ActivityRecord
      "invalid"    — hard errors, do NOT create ActivityRecord
      "suspicious" — parsed but flagged for analyst review
      "skipped"    — intentionally skipped (empty row, summary row, header)
    """

    def __init__(
        self,
        status: str,
        raw_payload: Dict[str, Any],
        errors: Optional[List[str]] = None,
        normalized_data: Optional[Dict[str, Any]] = None,
    ):
        self.status = status
        self.raw_payload = raw_payload
        self.errors = errors or []
        self.normalized_data = normalized_data or {}


class BaseParser(ABC):
    """
    Abstract base for all data-source parsers.

    Subclasses must implement validate_file() and parse_rows().
    Helper methods (detect_encoding) are provided here.
    """

    def __init__(self, organization, ingestion_run):
        self.organization = organization
        self.ingestion_run = ingestion_run

    @abstractmethod
    def validate_file(self, file_obj) -> bool:
        """
        Quick structural validation — called before committing to a full parse.
        If this returns False, the IngestionRun is marked "failed" immediately.
        """

    @abstractmethod
    def parse_rows(self, file_obj) -> Generator[ParseResult, None, None]:
        """
        Yield one ParseResult per logical row in the source file.

        Implementations must:
        - Yield a "skipped" result for intentionally ignored rows (empty, headers, totals).
        - Yield "invalid" for rows with hard errors; the pipeline skips ActivityRecord creation.
        - Yield "suspicious" for rows that parsed but have data-quality warnings.
        - Yield "valid" only when there are no errors AND no warnings.
        """

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def detect_encoding(self, file_obj) -> str:
        """
        Auto-detect the file's character encoding using chardet.

        SAP exports vary: UTF-8, Windows-1252 (Latin-1), and occasionally
        ISO-8859-1. Getting this wrong turns umlauts (ä, ö, ü) into garbage,
        which breaks plant-code matching and material descriptions.
        """
        import chardet
        raw = file_obj.read(8192)   # Sample 8 KB — enough for reliable detection
        file_obj.seek(0)
        result = chardet.detect(raw)
        encoding = result.get("encoding") or "utf-8"
        # chardet sometimes returns "ascii" for plain files; treat as utf-8
        if encoding.lower() == "ascii":
            encoding = "utf-8"
        return encoding