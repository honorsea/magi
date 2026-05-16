"""
MAGI Framework — Manufacturing Agentive Generative Intelligence
"""
import warnings
warnings.filterwarnings("ignore")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from magi.digital.config import ConfigState
from magi.digital.twin import DigitalTwin
from magi.digital.tool_api import ToolAPI
from magi.digital.replication import ReplicationRunner
from magi.digital.models import SimulationResult, TaskRecord, PhysioRecord

__all__ = [
    "ConfigState", "DigitalTwin", "ToolAPI", "ReplicationRunner",
    "SimulationResult", "TaskRecord", "PhysioRecord",
]
