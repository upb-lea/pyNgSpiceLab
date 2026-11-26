"""
Trigger Handler Module.

This module performs the dynamic stopping of the simulation based on a trigger condition provided by the user.
"""

# python libraries
import logging
import difflib
import operator
from abc import ABC, abstractmethod
from enum import Enum
from collections import deque
from typing import Callable

# 3rd party libraries

# own libraries
from .ngspice_wrapper import NgspiceWrapper

# configure root logger
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


class TriggerCondition(ABC):
    """An abstract class for defining different trigger conditions."""

    @property
    @abstractmethod
    def signal(self) -> str:
        """
        Return the name of the simulation signal that the trigger observes.

        :return: Name of the observed signal
        :rtype: str
        """
        pass

    @abstractmethod
    def evaluate(self, values: dict[str, float]) -> bool:
        """
        Evaluate the trigger condition against new simulation data.

        Note: the concrete sub-classes below receive a dict of signal name to value
        (see their own evaluate methods) instead of a single float.

        :param values: Latest simulation data used to evaluate the condition
        :type values: dict[str, float]
        :return: True, if the trigger condition is met
        :rtype: bool
        """
        pass


class ComparisonOperator(Enum):
    """Enum of the supported comparison operators, each bound to its callable from the operator module."""

    GT = (">", operator.gt)
    LT = ("<", operator.lt)
    EQ = ("==", operator.eq)
    GE = (">=", operator.ge)
    LE = ("<=", operator.le)
    NE = ("!=", operator.ne)

    _func: Callable[[float, float], bool]

    def __new__(cls, symbol: str, func: Callable[[float, float], bool]) -> "ComparisonOperator":
        """
        Create an enum member whose value is the operator symbol and which stores the comparison function.

        :param symbol: Operator symbol used as the enum value (e.g. '>=')
        :type symbol: str
        :param func: Comparison function that implements the operator
        :type func: Callable[[float, float], bool]
        :return: The new enum member
        :rtype: ComparisonOperator
        """
        obj = object.__new__(cls)
        obj._value_ = symbol
        obj._func = func
        return obj

    def __call__(self, a: float, b: float) -> bool:
        """
        Apply the comparison operator to two numbers.

        :param a: Left operand
        :type a: float
        :param b: Right operand
        :type b: float
        :return: Result of the comparison 'a <operator> b'
        :rtype: bool
        """
        return self._func(a, b)

    @classmethod
    def from_symbol(cls, symbol: str) -> "ComparisonOperator":
        """
        Retrieve a comparison operator using its symbol.
        
        :param symbol: Operator symbol in string format
        :type symbol: str
        :return: Member function of class corresponding to the symbol
        :rtype: ComparisonOperator
        """
        for member in cls:
            if member.value == symbol:
                return member

        raise ValueError(f"Unsupported comparison operator: {symbol}")

class ThresholdTrigger(TriggerCondition):
    """Trigger that fires when a signal compares true against a fixed threshold (e.g. 'v(out) > 1.5')."""

    _signal: str  # name of the observed signal
    _operator_str: str  # unused annotation, the operator is stored in _comparison
    _threshold: float  # value the signal is compared against

    def __init__(self, signal: str, threshold: float, op_str: ComparisonOperator):
        """
        Initialize the threshold trigger.

        :param signal: Name of the signal to observe
        :type signal: str
        :param threshold: Value the signal is compared against
        :type threshold: float
        :param op_str: Comparison operator applied as 'signal <operator> threshold'
        :type op_str: ComparisonOperator
        """
        self._signal = signal
        self._comparison = op_str  # raises ValueError if unknown
        self._threshold = threshold

    @property
    def signal(self) -> str:
        """
        Return the name of the observed signal.

        :return: Name of the observed signal
        :rtype: str
        """
        return self._signal

    def evaluate(self, values: dict[str, float]) -> bool:
        """
        Compare the current signal value against the threshold.

        :param values: Current simulation values, keyed by signal name
        :type values: dict[str, float]
        :return: True, if the comparison holds
        :rtype: bool
        """
        return self._comparison(values[self._signal], self._threshold)


class CrossDirection(Enum):
    """Enum of the supported threshold crossing directions."""

    RISING = "rising"
    FALLING = "falling"
    CROSS = "cross"  # Both directions


class CrossingTrigger(TriggerCondition):
    """Trigger that fires when a signal crosses a threshold in the requested direction."""

    def __init__(self, signal: str, threshold: float, direction: CrossDirection):
        """
        Initialize the crossing trigger.

        :param signal: Name of the signal to observe
        :type signal: str
        :param threshold: Value that has to be crossed
        :type threshold: float
        :param direction: Crossing direction that fires the trigger
        :type direction: CrossDirection
        """
        self._signal = signal
        self._threshold = threshold
        self._direction = direction
        self._prev: float | None = None  # previous sample, None until the first one arrives

    @property
    def signal(self) -> str:
        """
        Return the name of the observed signal.

        :return: Name of the observed signal
        :rtype: str
        """
        return self._signal

    def evaluate(self, values: dict[str, float]) -> bool:
        """
        Check whether the signal crossed the threshold between the previous and the current sample.

        :param values: Current simulation values, keyed by signal name
        :type values: dict[str, float]
        :return: True, if a crossing in the configured direction occurred
        :rtype: bool
        """
        value = values[self._signal]
        # Store the current value and keep the previous one for the comparison
        prev, self._prev = self._prev, value
        if prev is None:          # first sample: no crossing possible
            return False

        rising = prev < self._threshold <= value
        falling = prev > self._threshold >= value

        if self._direction is CrossDirection.RISING:
            return rising
        if self._direction is CrossDirection.FALLING:
            return falling
        return rising or falling


class WindowStatistic(Enum):
    """Enum of the statistics that can be computed over a sliding window."""

    RANGE = "range"
    AVG = "avg"


class SlidingWindowTrigger(TriggerCondition):
    """Trigger that fires when a statistic of a signal over a sliding time window compares true against a threshold."""

    def __init__(self, signal: str, statistic: WindowStatistic, op_str: ComparisonOperator, threshold: float, window: float):
        """
        Initialize the sliding window trigger.

        :param signal: Name of the signal to observe
        :type signal: str
        :param statistic: Statistic computed over the window
        :type statistic: WindowStatistic
        :param op_str: Comparison operator applied as 'statistic <operator> threshold'
        :type op_str: ComparisonOperator
        :param threshold: Value the statistic is compared against
        :type threshold: float
        :param window: Window length in simulation time
        :type window: float
        """
        self._signal = signal
        self._statistic = statistic
        self._comparison = op_str
        self._threshold = threshold
        self._window = window
        self._samples: deque[tuple[float, float]] = deque()  # (time, value)
        self._integral = 0.0                                  # running trapezoid integral
        self._start_time: float | None = None  # simulation time of the first sample

    @property
    def signal(self) -> str:
        """
        Return the name of the observed signal.

        :return: Name of the observed signal
        :rtype: str
        """
        return self._signal

    def evaluate(self, values: dict[str, float]) -> bool:
        """
        Add the new sample to the window and compare the window statistic against the threshold.

        :param values: Current simulation values, keyed by signal name (must also contain 'time')
        :type values: dict[str, float]
        :return: True, if a full window has elapsed and the comparison holds
        :rtype: bool
        """
        t, v = values["time"], values[self._signal]
        if self._start_time is None:
            self._start_time = t

        # add the new sample and extend the running integral
        if self._samples:
            t_prev, v_prev = self._samples[-1]
            self._integral += 0.5 * (v + v_prev) * (t - t_prev)
        self._samples.append((t, v))

        # drop samples that left the window (keep one at or before the window start)
        while len(self._samples) > 1 and self._samples[1][0] <= t - self._window:
            (ta, va), (tb, vb) = self._samples[0], self._samples[1]
            self._integral -= 0.5 * (va + vb) * (tb - ta)
            self._samples.popleft()

        # don't judge until a full window of simulation time has passed
        if t - self._start_time < self._window:
            return False

        return self._comparison(self._compute(t), self._threshold)

    def _compute(self, t: float) -> float:
        """
        Compute the configured statistic over the samples currently in the window.

        :param t: Current simulation time
        :type t: float
        :return: Time-weighted average for AVG, or max minus min for RANGE
        :rtype: float
        """
        if self._statistic is WindowStatistic.AVG:
            # Time-weighted average from the running integral
            span = t - self._samples[0][0]
            return self._integral / span if span > 0 else self._samples[-1][1]

        vals = [s[1] for s in self._samples]
        if self._statistic is WindowStatistic.RANGE:
            return max(vals) - min(vals)


class TriggerHandler:
    """Class that parses the user trigger condition and stops the simulation once the condition is met."""

    def __init__(self, trigger_condition: str, ngspice_object: NgspiceWrapper):
        """
        Initialize the trigger handler and create the trigger from its text description.

        :param trigger_condition: Trigger condition text (e.g. 'v(out) > 1.5')
        :type trigger_condition: str
        :param ngspice_object: Ngspice wrapper that is stopped when the trigger fires
        :type ngspice_object: NgspiceWrapper
        :raises ValueError: If the trigger condition format is not supported
        """
        self._trigger_condition = self._create_trigger(trigger_condition)
        self._ngspice_object = ngspice_object
        self._is_triggered = False
        self._signal_checked = False   # have we validated the signal name yet?
        self._signal_missing = False   # True if the signal doesn't exist in the data from ngspice

    def on_simulation_data(self, values: dict[str, float], step_index: int) -> None:
        """
        Handle new simulation data, evaluate the trigger and halt the simulation if it fires.

        :param values: Current simulation values, keyed by signal name
        :type values: dict[str, float]
        :param step_index: Index of the current simulation step
        :type step_index: int
        """
        # Nothing to do once fired or if the signal is unavailable
        if self._is_triggered or self._signal_missing:
            return

        signal_name = self._trigger_condition.signal

        # Validate the signal name once, on the first data callback
        if not self._signal_checked:
            self._signal_checked = True
            if signal_name not in values:
                self._signal_missing = True
                self._warn_signal_not_found(signal_name, values)
                return

        if self._trigger_condition.evaluate(values):
            self._is_triggered = True
            logger.info(f"Trigger fired at step {step_index}, halting simulation.")
            self._ngspice_object.stop()

    def _warn_signal_not_found(self, signal_name: str, values: dict[str, float]) -> None:
        """
        Log a warning that the trigger signal is missing, with close-match suggestions and the available signals.

        :param signal_name: Name of the signal that was not found
        :type signal_name: str
        :param values: Current simulation values, keyed by signal name
        :type values: dict[str, float]
        :return: None
        :rtype: None
        """
        available = sorted(values.keys())
        # Suggest up to three similar signal names
        suggestions = difflib.get_close_matches(signal_name, available, n=3)

        logger.warning(
            f"Trigger signal '{signal_name}' was not found in the simulation data. "
            f"The trigger is disabled and the simulation will run for the full simulation time."
        )
        if suggestions:
            logger.warning(f"Did you mean: {suggestions}?")
        logger.warning(f"Available signals ({len(available)}): {available}")

    @staticmethod
    def _create_trigger(trigger_condition: str) -> TriggerCondition:
        """
        Parse the trigger condition text and create the matching trigger object.

        Supported formats:
          - '<signal> <operator> <threshold>'
          - '<signal> rising|falling|cross <threshold>'
          - '<signal> range|avg <operator> <threshold> <window>'

        :param trigger_condition: Trigger condition text
        :type trigger_condition: str
        :return: Trigger object that represents the condition
        :rtype: TriggerCondition
        :raises ValueError: If the trigger condition format is not supported
        """
        parts = trigger_condition.split()

        # Condition 1: "<signal> operator <threshold>"
        if len(parts) == 3 and parts[1] in {c.value for c in ComparisonOperator}:
            signal, op_str, threshold = parts
            operation = ComparisonOperator.from_symbol(op_str)
            return ThresholdTrigger(signal, float(threshold), operation)

        # Condition 2: "<signal> rising|falling|cross <threshold>"
        if len(parts) == 3 and parts[1] in {d.value for d in CrossDirection}:
            signal, cross_direction, threshold = parts
            direction = CrossDirection(cross_direction)
            return CrossingTrigger(signal, float(threshold), direction)

        # Condition 3: "<signal> range <max_range> <window>"
        if len(parts) == 5 and parts[1] in {s.value for s in WindowStatistic} and parts[2] in {c.value for c in ComparisonOperator}:
            signal, stat, op_str, threshold, window = parts
            return SlidingWindowTrigger(signal, WindowStatistic(stat), ComparisonOperator.from_symbol(op_str), float(threshold), float(window))

        raise ValueError(f"Unsupported trigger condition: '{trigger_condition}'.")
