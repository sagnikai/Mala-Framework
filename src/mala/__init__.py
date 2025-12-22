"""
MALA: Multi-Agent Legacy Architecture
A Framework for Multi-Agent AI Integration in Legacy Industrial Systems

DOI: 10.5281/zenodo.19954858
"""

from .core import MALACore
from .agents.gatherer import GathererAgent
from .agents.planner import PlannerAgent
from .agents.critic import CriticAgent
from .models import (
    SafetyConstraint,
    CMDPState,
    CMDPAction,
    TemperatureBin,
    YardOccupancyBin,
    ManganeseVarianceBin,
    FreshnessScore,
    ConfidenceScore,
    KnowledgeSet,
    JustificationLog
)
from .gism import GISM
from .cdp import ContextualDataPolisher
from .adapters.ocr import TerminalOCRAdapter
from .adapters.csv_adapter import CSVArchiveAdapter
from .adapters.pdf_adapter import PDFParserAdapter
from .adapters.sql_adapter import SQL92Adapter

__version__ = "0.1.0"
__author__ = "Sagnik Mukherjee"
__doi__ = "10.5281/zenodo.19954858"

__all__ = [
    "MALACore",
    "GathererAgent",
    "PlannerAgent",
    "CriticAgent",
    "SafetyConstraint",
    "CMDPState",
    "CMDPAction",
    "TemperatureBin",
    "YardOccupancyBin",
    "ManganeseVarianceBin",
    "FreshnessScore",
    "ConfidenceScore",
    "KnowledgeSet",
    "JustificationLog",
    "GISM",
    "ContextualDataPolisher",
    "TerminalOCRAdapter",
    "CSVArchiveAdapter",
    "PDFParserAdapter",
    "SQL92Adapter",
]
