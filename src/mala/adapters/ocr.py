from .base import BaseAdapter

class TerminalOCRAdapter(BaseAdapter):
    """Simulated OCR adapter that reads from legacy terminals."""
    
    def __init__(self, simulate_unsafe: bool = False):
        self.simulate_unsafe = simulate_unsafe

    def scrape(self, target: str) -> str:
        """
        Simulates extracting text from a terminal.
        If simulate_unsafe is True, returns a value that violates the typical 1550C constraint.
        """
        if target == "FURNACE_VIEW":
            if self.simulate_unsafe:
                return "[2026-05-04 10:14:00] FURNACE_STATUS: ACTIVE | TMP 1580 | ALARM: OVERHEAT WARNING"
            else:
                return "[2026-05-04 10:14:00] FURNACE_STATUS: ACTIVE | TMP 1548 | ALARM: NONE"
        
        return f"UNKNOWN_TARGET: {target}"
