"""Per-agent circuit breaker."""
import time, logging
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, agent_name: str, failure_threshold: int = 3,
                 recovery_timeout: float = 30.0):
        self.agent_name        = agent_name
        self._threshold        = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state            = CircuitState.CLOSED
        self._failures         = 0
        self._last_failure: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure > self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("CircuitBreaker[%s]: OPEN → HALF_OPEN", self.agent_name)
        return self._state

    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def record_success(self):
        if self._state != CircuitState.CLOSED:
            logger.info("CircuitBreaker[%s]: → CLOSED", self.agent_name)
        self._state = CircuitState.CLOSED; self._failures = 0

    def record_failure(self):
        self._failures += 1; self._last_failure = time.time()
        if self._failures >= self._threshold or self._state == CircuitState.HALF_OPEN:
            if self._state != CircuitState.OPEN:
                logger.warning("CircuitBreaker[%s]: → OPEN (failures=%d)",
                               self.agent_name, self._failures)
            self._state = CircuitState.OPEN
