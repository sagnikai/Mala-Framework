from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """
    Abstract base class for all legacy system adapters.

    Each concrete adapter wraps one ingestion channel (OCR terminal,
    SQL-92 ERP, CSV archive, or scanned PDF) and exposes a uniform
    ``scrape`` interface so the GathererAgent can call any source
    without knowing its underlying protocol.  This is the "Bridge"
    tier described in Section 3.1 of the paper.
    """

    @abstractmethod
    def scrape(self, target: str) -> str:
        """
        Extract raw text data from the target system.

        Args:
            target: Source-specific identifier (view name, query
                    string, filename, etc.).

        Returns:
            Raw text string ready for downstream normalization.
        """
        pass
