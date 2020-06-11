import argparse
from collections import deque 
import enum
import math
import numpy as np
from pprint import pprint
import pulp as pl
import random
import time

import Parser
from PeopleAndSets import SetConstraint, SetConstraintType
import pulp_utils
from Solver import Solver, SolverStatus
from Schedule import Schedule


class SimpleBnbSolver(Solver):
    """Simple Branch and Bound solver."""
    def __init__(self, people, set_constraints, time_limit=-1):
        super(SimpleBnbSolver, self).__init__(people, set_constraints, time_limit)
        self.num_days = len(people[0].dateList)
        self.best_value = 0
        self.best_solution = None
        self.nodes = []
        self.status = SolverStatus.UNSOLVED


    def solve(self):
        start_time = time.time()
        total_lp_solve_time = 0

        # Create branching options for root
        branching_options = []
        for person in self.people:
            for day in range(1, self.num_days + 1):
                branching_options.append(BranchingOption(DecisionType.PERSON_DAY, person.uid, day))

        for set_constraint in set_constraints:
            if set_constraint.constraintType.value == SetConstraintType.DEPARTMENT.value:
                lower_bound = set_constraint.low_bound
                upper_bound = set_constraint.up_bound
                if upper_bound < 0:
                    upper_bound = len(set_constraint.personList)
                
                for day in range(1, self.num_days + 1):
                    branching_options.append(BranchingOption(DecisionType.DEPT_DAY, set_constraint.sid, 
                                                            day, lower_bound, upper_bound))

            elif set_constraint.constraintType.value == SetConstraintType.SYNERGY.value:
                for day in range(1, self.num_days + 1):
                    branching_options.append(BranchingOption(DecisionType.SYNERGY_DAY, set_constraint.sid, day))
            else:
                pass # Should not reach here unless new set constraint types are added


        root = BnbNode(None, branching_options)
        root.lp = pulp_utils.build_scheduling_lp(num_days, people, set_constraints)

        stack = deque()
        stack.append(root)

        count_explored_nodes = 0

        while stack: # implicit condition: stack is not empty
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                break

            node = stack.pop()
            count_explored_nodes += 1

            # print(node)

            children, lp_solve_time = node.branch()
            total_lp_solve_time += lp_solve_time

            # print('Node at depth {0}:\n\tLP value: {1:.2f}'.format(node.depth, node.lp_value))

            if node.feasible_value > self.best_value:
                self.best_value = node.feasible_value
                self.best_solution = node.feasible_solution

            # Pruning: Don't need to add children if LP relaxation has 
            # opt value no better than best feasible integer solution seen so far
            if node.lp_value <= self.best_value or len(children) == 0:
                continue

            for child in children:
                stack.append(child) # Push children onto stack for DFS


        # Print summary stats
        print('Explored {0:d} nodes.'.format(count_explored_nodes))
        print('Elapsed time: {0:.3f} s'.format(elapsed_time))
        print('Total LP solve time: {0:.3f} s'.format(total_lp_solve_time))
        print('Best value: {0:d}'.format(int(self.best_value)))

        # Update solver status
        if elapsed_time > time_limit and time_limit > 0:
            if self.best_value <= 0:
                self.status = SolverStatus.OUT_OF_TIME
            else:
                self.status = SolverStatus.FEASIBLE
        else:
            if self.best_value <= 0:
                self.status = SolverStatus.INFEASIBLE
            else:
                self.status = SolverStatus.OPTIMAL

        # Build and return best Schedule
        best_schedule = Schedule(people=self.people)
        best_schedule.buildFromSolutionVariables(self.best_solution)

        return best_schedule


class BnbNode(object):
    """
    Represents a node in the branch and bound tree.

    Fields:
    decisions - a list of Decision objects representing the branching decisions 
                that lead to this node. 
                The entry ``decisions[-1]`` is the Decision that 
                distinguishes this node from its parent.
    lp - A PuLP problem encoding the LP relaxation
    """
    def __init__(self, parent, branching_options, new_decision=None):
        if parent is None:
            self.decisions = []
            self.lp = None
            self.depth = 0
        else:
            self.decisions = parent.decisions.copy()
            self.decisions.append(new_decision)
            
            self.lp = parent.lp.copy()
            self.lp = new_decision.add_constraint_to_problem(self.lp)
            self.depth = parent.depth + 1

        self.feasible_value = 0
        self.lp_value = 0
        self.branching_options = branching_options.copy()


    def branch(self):
        """
        Randomly choose a decision on which to branch and
        return children with the appropriate parameters. 

        Returns an empty list if the current subproblem has an infeasible LP.
        """
        lp_solve_time = time.time()
        status = pulp_utils.solve_lp(self.lp)
        lp_solve_time = time.time() - lp_solve_time
        if status in ['Infeasible', 'Unbounded', 'Not Solved']:
            return [], lp_solve_time

        if status == 'Undefined':
            raise Exception('Solver fails with status \'Undefined\' for LP of node {0}.'.format(self))

        # Otherwise, status == 'Optimal', so we can check for a feasible integer solution and branch
        self.lp_value = pl.value(self.lp.objective)

        if pulp_utils.is_integral(self.lp):
            self.feasible_value = self.lp_value
            self.feasible_solution = pulp_utils.extract_solution(self.lp)
        else:
            # Try rounding LP solution in hopes of feasible integer solution
            for var in self.lp.variables():
                var.varValue = 0 if var.varValue <= 0.5 else 1

            feasible = True
            for constraint_name in self.lp.constraints:
                constraint = self.lp.constraints[constraint_name]
                value = pl.value(constraint)

                violated = ((value > 0 and constraint.sense == pl.LpConstraintLE) or 
                            (value < 0 and constraint.sense == pl.LpConstraintGE))
                if violated:
                    # print('Violated constraint:\n\t{0}'.format(constraint))
                    feasible = False
                    break

            if feasible:
                self.lp_value = pl.value(self.lp.objective)
                self.feasible_value = self.lp_value
                self.feasible_solution = pulp_utils.extract_solution(self.lp)

        children = []

        branching_option = random.choice(self.branching_options)
        new_branching_options = self.branching_options.copy()
        new_branching_options.remove(branching_option)

        # print('Node {0} branching on {1}'.format(self, branching_option))

        if branching_option.decision_type.value in [DecisionType.PERSON_DAY.value, DecisionType.SYNERGY_DAY.value]:
            for direction in [0, 1]:
                children.append(BnbNode(self, new_branching_options, BranchingDecision(branching_option, direction)))
        
        elif branching_option.decision_type.value == DecisionType.DEPT_DAY.value:
            difference = branching_option.upper_bound - branching_option.lower_bound
            if difference <= 0:
                # print('dept day constraint with same LB/UB')
                return children, lp_solve_time # Department attendance is actually fixed for the given day
            
            threshold = branching_option.lower_bound + (difference // 2)
            
            # threshold replaces upper bound:
            branching_option_lower_half = BranchingOption(DecisionType.DEPT_DAY, branching_option.entity_id, branching_option.day, branching_option.lower_bound, threshold)
            child_0 = BnbNode(self, new_branching_options, BranchingDecision(branching_option, 0, threshold))
            child_0.branching_options.append(branching_option_lower_half)
            children.append(child_0)

            # threshold + 1 replaces lower bound:
            branching_option_upper_half = BranchingOption(DecisionType.DEPT_DAY, branching_option.entity_id, branching_option.day, threshold + 1, branching_option.upper_bound)
            child_1 = BnbNode(self, new_branching_options, BranchingDecision(branching_option, 1, threshold))
            child_1.branching_options.append(branching_option_upper_half)
            children.append(child_1)

        else:
            raise Exception('Unrecognized or unimplemented decision type: {0}'.format(branching_option.decision_type))

        return children, lp_solve_time


    def __str__(self):
        return 'Depth: {0:02d}'.format(self.depth)#\n\tDecisions: {1}'.format(self.depth, self.decisions)


class BranchingOption(object):
    """
    Represents a branching option. 

    Fields:
    decision_type - an instance of DecisionType
    entity_id - the person or set id related to the decision
    day - the 1-based index of the day corresponding to the decision
    lower_bound - only used for DecisionType.DEPT_DAY
    upper_bound - only used for DecisionType.DEPT_DAY
    """
    def __init__(self, decision_type, entity_id, day, lower_bound=None, upper_bound=None):
        if not isinstance(decision_type, DecisionType):
            raise Error('Must provide a valid DecisionType.')

        self.decision_type = decision_type
        self.entity_id = entity_id
        self.day = day
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound


    def __str__(self):
        return '{0}: id={1}, day={2}'.format(self.decision_type, self.entity_id, self.day)


class BranchingDecision(object):
    """
    Represents a branching decision, that is, 
    a BranchingOption with a direction field. 

    Fields:
    branching_option - an instance of BranchingOption
    direction - 0 for <= or fixed at 0; 1 for >= or fixed at 1
    threshold - the RHS threshold P, used only for DecisionType.DEPT_DAY
                (either <= P or >= P + 1 from dept. in office on a given day)
    """
    def __init__(self, branching_option, direction, threshold=None):
        self.branching_option = branching_option
        self.direction = direction
        self.threshold = threshold


    def add_constraint_to_problem(self, problem):
        """
        Converts this branching decision to a PuLP LpConstraint object
        to be added to the given PuLP problem. 
        Returns the updated problem. 
        """
        if self.branching_option.decision_type.value == DecisionType.PERSON_DAY.value:
            uid = self.branching_option.entity_id
            day = self.branching_option.day
            var_name = '{0}_{1}_{2}'.format(pulp_utils.SCHEDULE_VAR_PREFIX, uid, day)
            for var in problem.variables():
                if var.name == var_name:
                    problem += var == self.direction, 'Make_{0}_{1}work_day_{2}'.format(uid, '' if self.direction == 1 else 'not_', day)
                    break
        elif self.branching_option.decision_type.value == DecisionType.SYNERGY_DAY.value:
            sid = self.branching_option.entity_id
            day = self.branching_option.day
            var_name = '{0}_{1}_{2}'.format(pulp_utils.SYNERGY_VAR_PREFIX, sid, day)
            for var in problem.variables():
                if var.name == var_name:
                    description = 'Make_{0}_all_work_day_{1}'.format(sid, day) if self.direction == 1 else 'Allow_{0}_not_all_work_day_{1}'.format(sid, day)
                    problem += var == self.direction, description
                    break
        elif self.branching_option.decision_type.value == DecisionType.DEPT_DAY.value:
            sid = self.branching_option.entity_id
            day = self.branching_option.day

            if self.direction == 0:
                # Copy upper bound constraint and use threshold as new upper bound
                try:
                    constraint = problem.constraints['{0}_UB_day_{1}'.format(sid, day)].copy()
                except KeyError as e:
                    # Upper bound constraint may not exist, but we always have a lower bound constraint
                    constraint = problem.constraints['{0}_LB_day_{1}'.format(sid, day)].copy()
                    constraint.sense = pl.LpConstraintLE # Change to UB constraint
                constraint.changeRHS(self.threshold)
                problem += constraint
            else: # self.direction == 1
                # Copy lower bound constraint and use threshold + 1 as new lower bound
                constraint = problem.constraints['{0}_LB_day_{1}'.format(sid, day)].copy()
                constraint.changeRHS(self.threshold + 1)
                problem += constraint
        else:
            raise Exception('Unrecognized or unimplemented decision type: {0}'.format(branching_option.decision_type))

        return problem


class DecisionType(enum.Enum):
    PERSON_DAY = 0 # A person is assigned to (not) work on a certain day
    SYNERGY_DAY = 1 # A team (synergy constraint) is (not) required to all work on a certain day
    DEPT_DAY = 2 # A department's lower or upper bound is adjusted for a certain day


if __name__ == '__main__':
    commandLineParser = argparse.ArgumentParser(description='Takes an integer and two csv files and parses them for the office scheduler')
    commandLineParser.add_argument('numdays', type=int, help="the total number of days to schedule for")
    commandLineParser.add_argument('peopleFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the people being scheduled")
    commandLineParser.add_argument('setFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the department and synergy constraints")

    args = commandLineParser.parse_args()

    num_days, people, set_constraints = Parser.parseCSVs(n=args.numdays, peopleFile=args.peopleFile, setFile=args.setFile)
    time_limit = 30

    bnb_solver = SimpleBnbSolver(people, set_constraints, time_limit=time_limit)
    schedule = bnb_solver.solve()

    print('Status:', bnb_solver.status)

    # import pdb; pdb.set_trace()

    print('Schedule:', schedule)
