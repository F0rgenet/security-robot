import logging
from enum import Enum, auto
from common.command import Command
from broker import CommandSender
from common.logged import LoggedClass

class RobotState(Enum):
    IDLE = auto()
    SEARCHING_TARGET = auto()
    ADJUSTING_ANGLE = auto()
    MOVING_TO_TARGET = auto()
    TARGET_REACHED = auto()

class RobotFSM(LoggedClass):
    DISTANCE_THRESHOLD_STOP = 50
    ANGLE_THRESHOLD_STRAIGHT = 10
    TARGET_LOST_COUNT_THRESHOLD = 10

    def __init__(self, commands_sender: CommandSender):
        self.state = RobotState.IDLE
        self.broker = commands_sender
        self.target_lost = 0
        self.last_cmd = None
        self.search_dir = Command.TURN_LEFT
        super().__init__()
        self.logger.info(f"FSM init: {self.state}")

    def _send(self, cmd: Command):
        if cmd != self.last_cmd:
            self.broker.send(cmd)
            self.last_cmd = cmd

    def update(self, data: dict):
        dist = data.get('distance_px')
        ang = data.get('angle_to_target_deg')
        # handle lost/found omitted for brevity...
        # example: in IDLE
        if self.state == RobotState.IDLE:
            self._send(Command.STOP)
            if dist is not None and ang is not None:
                self.state = RobotState.ADJUSTING_ANGLE
        # implement other handlers similarly

# Example usage
if __name__ == '__main__':
    mqtt = CommandSender()
    mqtt.connect()
    fsm = RobotFSM(mqtt)
    fsm._send(Command.MOVE_FORWARD)
    # then in loop: fsm.update(camera_data)