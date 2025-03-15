from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any

class Command(Enum):
    MOVE_FORWARD = "move_forward"
    TURN_RIGHT = "turn_right"
    TURN_LEFT = "turn_left"
    STOP = "stop"

    
@dataclass
class CommandWithArguments:
    command: Command
    args: Dict[str, Any] = field(default_factory=dict)
