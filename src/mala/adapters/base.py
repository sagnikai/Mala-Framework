from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """Abstract base class for legacy system adapters."""
    
    @abstractmethod
    def scrape(self, target: str) -> str:
        """Extracts raw text data from the target system."""
        pass
