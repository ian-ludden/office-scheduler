from abc import ABC, abstractmethod
import enum

class Solver(ABC):
    """Abstract superclass for solvers of the office scheduling problem."""
    def __init__(self, people=[], set_constraints=[], time_limit=-1):
        self.people = people
        self.set_constraints = set_constraints
        self.time_limit = time_limit
        self.status = SolverStatus.NOT_SOLVED
        self.solution = None


    @abstractmethod
    def solve(self):
        pass


class SolverStatus(enum.Enum):
    """Enumerated constants for solver status."""
    NOT_SOLVED = 0 # Have not tried to solve
    OPTIMAL = 1 # Solved to optimality (certified)
    FEASIBLE = 2 # Found a feasible solution but didn't have time to certify optimality
    INFEASIBLE = -1 # Problem is infeasible (certified)
    OUT_OF_TIME = -2 # Ran out of time before finding a feasible solution or determining infeasible/unbounded
    UNBOUNDED = 3 # Problem objective can be arbitrarily large (if maximizing; arbitrarily small, if minimizing)

