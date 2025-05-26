# system/control.py

import logging
from enum import Enum, auto
# Эти импорты здесь не нужны, т.к. FSM только определяет действие,
# а отправкой занимается main.py
# from common.command import Command
# from broker import CommandSender
# from common.logged import LoggedClass

class RobotAction:
    def __init__(self, command: str, speed: float = 0.0, turn_angle_change: float = 0.0):
        self.command = command
        # speed и turn_angle_change могут быть полезны для отладки или если робот поддерживает
        # команды с параметрами скорости/угла, но ваш текущий engine.py их не использует.
        self.speed = speed
        self.turn_angle_change = turn_angle_change

    def __repr__(self):
        return f"RobotAction(command='{self.command}', speed={self.speed}, turn_angle_change={self.turn_angle_change})"

class State:
    def __init__(self, fsm):
        self.fsm = fsm

    def enter(self, **kwargs):
        # print(f"Entering state: {self.__class__.__name__}") # Для отладки
        pass

    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        raise NotImplementedError

    def exit(self):
        # print(f"Exiting state: {self.__class__.__name__}") # Для отладки
        pass

class IdleState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        return RobotAction(command="idle")

class OrientingState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        # Проверяем, находится ли угол в пределах +- straight_angle_threshold
        if abs(angle_to_target) > self.fsm.straight_angle_threshold:
            # Угол слишком большой, нужно поворачивать
            if angle_to_target > 0: # Цель справа
                return RobotAction(command="turn_right", speed=self.fsm.turn_speed, turn_angle_change=angle_to_target)
            else: # Цель слева
                return RobotAction(command="turn_left", speed=self.fsm.turn_speed, turn_angle_change=angle_to_target)
        else:
            # Угол в допустимых пределах для движения прямо, переходим в MOVING_FORWARD
            self.fsm.transition_to(self.fsm.states[RobotStates.MOVING_FORWARD])
            # Сразу выполняем действие нового состояния, чтобы не терять цикл обработки
            return self.fsm.current_state.execute(angle_to_target, distance_to_target)

class MovingForwardState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        if distance_to_target <= self.fsm.distance_tolerance:
            # Цель достигнута
            self.fsm.transition_to(self.fsm.states[RobotStates.GOAL_REACHED])
            return RobotAction(command="stop") # Или "idle", в зависимости от желаемого поведения
        elif abs(angle_to_target) > self.fsm.straight_angle_threshold:
            # Во время движения угол вышел за пределы допустимого, нужно снова ориентироваться
            self.fsm.transition_to(self.fsm.states[RobotStates.ORIENTING])
            # Сразу выполняем действие нового состояния
            return self.fsm.current_state.execute(angle_to_target, distance_to_target)
        else:
            # Угол в норме, дистанция до цели еще есть - едем вперед
            return RobotAction(command="move_forward", speed=self.fsm.move_speed)

class GoalReachedState(State):
    def execute(self, angle_to_target: float, distance_to_target: float) -> RobotAction:
        # Можно вернуть "stop", чтобы робот остановился, или "idle", если это разные понятия.
        # Для простоты, "stop" хорошо подходит.
        return RobotAction(command="stop")

class RobotStates(Enum):
    IDLE = auto()
    ORIENTING = auto()
    MOVING_FORWARD = auto()
    GOAL_REACHED = auto()

class RobotNavigationFSM:
    # Новый параметр для определения диапазона "прямо" (-X ... +X градусов)
    DEFAULT_STRAIGHT_ANGLE_THRESHOLD_DEG = 15.0

    def __init__(self, 
                 angle_tolerance: float, # Этот tolerance для первоначального грубого выравнивания из IDLE
                 distance_tolerance: float,
                 turn_speed: float, 
                 move_speed: float,
                 # Убираем angle_tolerance_while_moving, заменяем на straight_angle_threshold
                 straight_angle_threshold: float = DEFAULT_STRAIGHT_ANGLE_THRESHOLD_DEG):
        
        self.angle_tolerance = angle_tolerance # Для первоначального выравнивания из IDLE
        self.distance_tolerance = distance_tolerance
        self.turn_speed = turn_speed
        self.move_speed = move_speed
        self.straight_angle_threshold = straight_angle_threshold 

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
        # print(f"FSM Initialized. Initial state: {self.current_state_enum.name}, Straight Threshold: {self.straight_angle_threshold}")


    def transition_to(self, new_state_obj: State):
        if self.current_state == new_state_obj:
            return

        # old_state_name = self.current_state_enum.name
        self.current_state.exit()
        self.current_state = new_state_obj
        for enum_key, state_val in self.states.items():
            if state_val == new_state_obj:
                self.current_state_enum = enum_key
                break
        # print(f"FSM Transition: {old_state_name} -> {self.current_state_enum.name}") # Для отладки
        self.current_state.enter()

    def set_target(self, angle_to_target: float, distance_to_target: float):
        # print(f"FSM Set Target: angle={angle_to_target:.1f}, dist={distance_to_target:.1f}, Current State: {self.current_state_enum.name}")
        self._target_angle = angle_to_target
        self._target_distance = distance_to_target
        self._has_target = True

        # Логика перехода из IDLE или GOAL_REACHED при появлении новой цели
        if self.current_state_enum == RobotStates.IDLE or self.current_state_enum == RobotStates.GOAL_REACHED:
            if self._target_distance > self.distance_tolerance:
                # Сначала проверяем, не находимся ли мы УЖЕ в коридоре для прямого движения
                if abs(self._target_angle) <= self.straight_angle_threshold:
                    self.transition_to(self.states[RobotStates.MOVING_FORWARD])
                # Если нет, то используем angle_tolerance для более грубой начальной ориентации
                elif abs(self._target_angle) > self.angle_tolerance: # Если угол больше начального допуска
                    self.transition_to(self.states[RobotStates.ORIENTING])
                else: # Угол между straight_angle_threshold и angle_tolerance, тоже ориентируемся
                    self.transition_to(self.states[RobotStates.ORIENTING])
            else: # Цель сразу в зоне досягаемости
                self.transition_to(self.states[RobotStates.GOAL_REACHED])

    def update(self, current_angle_to_target: float, current_distance_to_target: float) -> RobotAction:
        # print(f"FSM Update: angle={current_angle_to_target:.1f}, dist={current_distance_to_target:.1f}, state={self.current_state_enum.name}, has_target={self._has_target}")
        
        # Обновляем информацию о цели, даже если она не изменилась, т.к. состояния могут на это реагировать
        self._target_angle = current_angle_to_target
        self._target_distance = current_distance_to_target

        if not self._has_target: # Если цель была потеряна (clear_target был вызван)
            if self.current_state_enum != RobotStates.IDLE:
                # print("FSM: Target lost (no data or clear_target called), transitioning to IDLE")
                self.transition_to(self.states[RobotStates.IDLE])
            # В состоянии IDLE, execute вернет RobotAction(command="idle")
            return self.current_state.execute(0.0, 0.0) 

        # Если мы в IDLE, но цель _только что_ появилась (например, set_target вызван),
        # и set_target уже должен был нас перевести. Но на всякий случай, если update вызван сразу после set_target
        # до того, как внешняя логика обработала переход.
        if self.current_state_enum == RobotStates.IDLE and self._has_target:
            # print("FSM: In IDLE but target is present. Re-evaluating initial transition based on current target.")
            if self._target_distance > self.distance_tolerance:
                if abs(self._target_angle) <= self.straight_angle_threshold:
                    self.transition_to(self.states[RobotStates.MOVING_FORWARD])
                elif abs(self._target_angle) > self.angle_tolerance:
                    self.transition_to(self.states[RobotStates.ORIENTING])
                else:
                    self.transition_to(self.states[RobotStates.ORIENTING])
            else:
                self.transition_to(self.states[RobotStates.GOAL_REACHED])
            # После принудительного перехода, сразу выполняем execute нового состояния
            return self.current_state.execute(self._target_angle, self._target_distance)
        
        # Для всех остальных активных состояний (ORIENTING, MOVING_FORWARD, GOAL_REACHED)
        action = self.current_state.execute(self._target_angle, self._target_distance)
        # print(f"FSM Action from {self.current_state_enum.name}: {action.command} (angle: {self._target_angle:.1f}, dist: {self._target_distance:.1f})")
        return action

    def clear_target(self):
        # print("FSM Clear Target called.")
        self._has_target = False
        # Если мы не в IDLE или GOAL_REACHED, и цель пропадает, переходим в IDLE
        if self.current_state_enum not in [RobotStates.IDLE, RobotStates.GOAL_REACHED]:
            self.transition_to(self.states[RobotStates.IDLE])

    def get_current_state_name(self) -> str:
        return self.current_state_enum.name