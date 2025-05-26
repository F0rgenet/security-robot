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


class RobotAction:
    def __init__(self, command: str, speed: float = 0.0, turn_angle_change: float = 0.0):
        self.command = command
        self.speed = speed
        self.turn_angle_change = turn_angle_change

    def __repr__(self):
        return f"RobotAction(command='{self.command}', speed={self.speed}, turn_angle_change={self.turn_angle_change})"

class State:
    def __init__(self, fsm):
        self.fsm = fsm

    def enter(self, **kwargs):
        pass

    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        raise NotImplementedError

    def exit(self):
        pass

class IdleState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        return RobotAction(command="idle")

class OrientingState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        if abs(angle_to_target) > self.fsm.angle_tolerance:
            if angle_to_target > 0:
                return RobotAction(command="turn_right", speed=self.fsm.turn_speed, turn_angle_change=angle_to_target)
            else:
                return RobotAction(command="turn_left", speed=self.fsm.turn_speed, turn_angle_change=angle_to_target)
        else:
            self.fsm.transition_to(self.fsm.states[RobotStates.MOVING_FORWARD])
            return self.fsm.current_state.execute(angle_to_target, distance_to_target)

class MovingForwardState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        if distance_to_target <= self.fsm.distance_tolerance:
            self.fsm.transition_to(self.fsm.states[RobotStates.GOAL_REACHED])
            return RobotAction(command="stop")
        elif abs(angle_to_target) > self.fsm.angle_tolerance_while_moving:
            self.fsm.transition_to(self.fsm.states[RobotStates.ORIENTING])
            return self.fsm.current_state.execute(angle_to_target, distance_to_target)
        else:
            return RobotAction(command="move_forward", speed=self.fsm.move_speed)

class GoalReachedState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        return RobotAction(command="stop")

class RobotStates(Enum):
    IDLE = auto()
    ORIENTING = auto()
    MOVING_FORWARD = auto()
    GOAL_REACHED = auto()

class RobotNavigationFSM:
    def __init__(self, angle_tolerance: float, distance_tolerance: float,
                 turn_speed: float, move_speed: float,
                 angle_tolerance_while_moving: float):
        self.angle_tolerance = angle_tolerance
        self.distance_tolerance = distance_tolerance
        self.turn_speed = turn_speed
        self.move_speed = move_speed
        self.angle_tolerance_while_moving = angle_tolerance_while_moving if angle_tolerance_while_moving is not None else angle_tolerance * 1.5

        self._target_angle: float = 0.0
        self._target_distance: float = 0.0
        self._has_target: bool = False

        self.states = {
            RobotStates.IDLE: IdleState(self),
            RobotStates.ORIENTING: OrientingState(self),
            RobotStates.MOVING_FORWARD: MovingForwardState(self),
            RobotStates.GOAL_REACHED: GoalReachedState(self),
        }
        self.current_state_enum = RobotStates.IDLE
        self.current_state: State = self.states[self.current_state_enum]
        self.current_state.enter()

    def transition_to(self, new_state_obj: State):
        if self.current_state == new_state_obj:
            return

        self.current_state.exit()
        self.current_state = new_state_obj
        for enum_key, state_val in self.states.items():
            if state_val == new_state_obj:
                self.current_state_enum = enum_key
                break
        self.current_state.enter()

    def set_target(self, angle_to_target: float, distance_to_target: float):
        self._target_angle = angle_to_target
        self._target_distance = distance_to_target
        self._has_target = True

        if self.current_state_enum == RobotStates.IDLE or self.current_state_enum == RobotStates.GOAL_REACHED:
            if self._target_distance > self.distance_tolerance:
                if abs(self._target_angle) > self.angle_tolerance:
                    self.transition_to(self.states[RobotStates.ORIENTING])
                else:
                    self.transition_to(self.states[RobotStates.MOVING_FORWARD])
            else:
                self.transition_to(self.states[RobotStates.GOAL_REACHED])

    def update(self, current_angle_to_target: float, current_distance_to_target: float) -> RobotAction:
        self._target_angle = current_angle_to_target
        self._target_distance = current_distance_to_target

        if not self._has_target and self.current_state_enum != RobotStates.IDLE:
            self.transition_to(self.states[RobotStates.IDLE])
            return self.current_state.execute(0.0, 0.0)

        if self.current_state_enum == RobotStates.IDLE and self._has_target:
            if self._target_distance > self.distance_tolerance:
                if abs(self._target_angle) > self.angle_tolerance:
                    self.transition_to(self.states[RobotStates.ORIENTING])
                else:
                    self.transition_to(self.states[RobotStates.MOVING_FORWARD])
            else:
                self.transition_to(self.states[RobotStates.GOAL_REACHED])
            # Fall through to execute the new state's logic with current target data
        
        action = self.current_state.execute(self._target_angle, self._target_distance)
        
        if not self._has_target and self.current_state_enum not in [RobotStates.IDLE, RobotStates.GOAL_REACHED]:
             self.transition_to(self.states[RobotStates.IDLE])
             return self.states[RobotStates.IDLE].execute(0.0,0.0)
             
        return action

    def clear_target(self):
        self._has_target = False
        if self.current_state_enum not in [RobotStates.IDLE, RobotStates.GOAL_REACHED]:
            self.transition_to(self.states[RobotStates.IDLE])

    def get_current_state_name(self) -> str:
        return self.current_state_enum.name