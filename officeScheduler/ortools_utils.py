# Utilities for solving office scheduling problem with Google OR-Tools package
import argparse
from ortools.linear_solver import pywraplp
import numpy as np
import time

from officeScheduler.PeopleAndSets import SetConstraintType
import officeScheduler.Parser
from officeScheduler.Solver import SolverStatus

SCHEDULE_VAR_PREFIX = 'Schedule'
SYNERGY_VAR_PREFIX = 'Synergy'
ORTOOLS_SOLVER_STATUS_TO_OURS_MAP = {0: SolverStatus.OPTIMAL, 
                                     1: SolverStatus.FEASIBLE,
                                     2: SolverStatus.INFEASIBLE,
                                     3: SolverStatus.UNBOUNDED,
                                     6: SolverStatus.NOT_SOLVED}

def build_scheduling_ilp(num_days, people, set_constraints):
    """
    Given outputs of Parser.parseCSVs(), 
    constructs a Google OR-Tools Solver representing the scheduling problem.
    The objective is to maximize the number of person-days. 
    """
    solver = pywraplp.Solver('office_scheduling_problem', 
                             # pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
                             pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING) # Can use CBC to solve MIPs

    # Find indices of 'synergy' set constraints
    synergy_indices = []
    for index, set_constraint in enumerate(set_constraints):
        if set_constraint.constraintType.value == SetConstraintType.SYNERGY.value:
            synergy_indices.append(index)

    synergy_sets = [set_constraints[i].sid for i in synergy_indices]
    days = range(1, num_days + 1)

    # Create relaxed decision variables 'Schedule_i_j' indicating whether person i is scheduled on day j
    variables = {}
    for person in people:
        for day in days:
            var_name = '{2}_{0}_{1}'.format(person.uid, day, SCHEDULE_VAR_PREFIX)
            person_day_var = solver.IntVar(0, 1, var_name) # Change to IntVar to enforce integer
            variables[var_name] = person_day_var

    # Create relaxed decision variables Synergy_k_j indicating whether team k is all present on day j
    for sid in synergy_sets:
        for day in days:
            var_name = '{2}_{0}_{1}'.format(sid, day, SYNERGY_VAR_PREFIX)
            synergy_day_var = solver.IntVar(0, 1, var_name) # Change to IntVar to enforce integer
            variables[var_name] = synergy_day_var

    # Add objective: sum of all Schedule_i_j variables
    objective = solver.Objective()
    for person in people:
        for day in days:
            var_name = '{2}_{0}_{1}'.format(person.uid, day, SCHEDULE_VAR_PREFIX)
            objective.SetCoefficient(variables[var_name], 1)
    objective.SetMaximization()

    # Add constraints for each person's availability:
    # Person i can only be scheduled on day j if their dateList entry for day j is True
    constraints = {}
    for person in people:
        for day in days:
            availability = int(person.dateList[day - 1])
            if availability == 0:
                constraint_name = '{0}_can\'t_work_on_day_{1}.'.format(person.uid, day)
                constraint = solver.Constraint(0, 0, constraint_name)
                var_name = '{2}_{0}_{1}'.format(person.uid, day, SCHEDULE_VAR_PREFIX)
                person_day_var = variables[var_name]
                constraint.SetCoefficient(person_day_var, 1)
                constraints[constraint_name] = constraint

    for index, set_constraint in enumerate(set_constraints):
        num_people = len(set_constraint.personList)
        if set_constraint.up_bound < 0:
            set_constraint.up_bound = num_people

        if set_constraint.constraintType.value == SetConstraintType.DEPARTMENT.value:
            # Add lower-/upper-bound constraints for each day
            for day in days:
                constraint_name = '{0}_bounds_day_{1}'.format(set_constraint.sid, day)
                constraint = solver.Constraint(set_constraint.low_bound, set_constraint.up_bound, constraint_name)
                constraints[constraint_name] = constraint
                for person_uid in set_constraint.personList:
                    var_name = 'Schedule_{0}_{1}'.format(person_uid, day)
                    person_day_var = variables[var_name]
                    constraint.SetCoefficient(person_day_var, 1)

        elif set_constraint.constraintType.value == SetConstraintType.SYNERGY.value:
            # Add lower-bound constraint for number of days with full set present
            constraint_name = 'Synergy_bound_{0}'.format(set_constraint.sid)
            constraint = solver.Constraint(set_constraint.low_bound, num_days, constraint_name)
            constraints[constraint_name] = constraint
            
            for day in days:
                var_name = '{2}_{0}_{1}'.format(set_constraint.sid, day, SYNERGY_VAR_PREFIX)
                synergy_day_var = variables[var_name]
                constraint.SetCoefficient(synergy_day_var, 1)

            # Add constraint to enforce all of set k showing up when y_{k,j} is 1
            for day in days:
                constraint_name = 'Synergy_enforced_{0}_day_{1}'.format(set_constraint.sid, day)
                constraint = solver.Constraint(0, num_people) # Only lower bound matters
                constraints[constraint_name] = constraint
    
                for person_uid in set_constraint.personList:
                    var_name = '{2}_{0}_{1}'.format(person_uid, day, SCHEDULE_VAR_PREFIX)
                    person_day_var = variables[var_name]
                    constraint.SetCoefficient(person_day_var, 1)

                synergy_var_name = '{2}_{0}_{1}'.format(set_constraint.sid, day, SYNERGY_VAR_PREFIX)
                synergy_day_var = variables[synergy_var_name]
                constraint.SetCoefficient(synergy_day_var, -1 * num_people)
        
        else:
            raise Exception('Invalid constraintType field for set constraint with id {0}:\n\t{1}'.format(set_constraint.sid, set_constraint.constraintType))
            pass
            # # Should never reach this case due to type validation in SetConstraint.__init__()
            # # Wait... Could reach this case if up_bound is -1 for a DEPARTMENT-type constraint
            # print('Ignoring unsupported set constraint: sid = {0}, type = {1}.'.format(set_constraint.sid, set_constraint.constraintType))

    return solver, variables, constraints


def solve_ilp(solver):
    """
    Calls the given ILP solver and returns the Google OR-Tools solver status code. 
    """
    status = solver.Solve()
    return status


def is_integral(solver):
    """
    Returns True if all variables in the current solution 
    to the given LP relaxation are integral; False otherwise.
    """
    for var in solver.variables():
        if var.solution_value() != int(var.solution_value()):
            return False

    return True


def extract_solution(solver):
    """
    Extracts the solution to the given LP solver, 
    returning a dictionary of variable names to values. 
    """
    solution = {}
    for var in solver.variables():
        solution[var.name()] = var.solution_value()

    return solution


if __name__ == '__main__':
    commandLineParser = argparse.ArgumentParser(description='Takes an integer and two csv files and parses them for the office scheduler')
    commandLineParser.add_argument('numdays', type=int, help="the total number of days to schedule for")
    commandLineParser.add_argument('peopleFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the people being scheduled")
    commandLineParser.add_argument('setFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the department and synergy constraints")

    args = commandLineParser.parse_args()

    num_days, people, set_constraints = Parser.parseCSVs(n=args.numdays, peopleFile=args.peopleFile, setFile=args.setFile)

    #TODO: currently converting dictionary to list; should evetually change to actually use the dictionary
    people=list(people.values())
    set_constraints=list(set_constraints.values())

    solver, variables, constraints = build_scheduling_ilp(num_days, people, set_constraints)

    print('No. variables:', solver.NumVariables())
    print('No. constraints:', solver.NumConstraints())
    # print('Constraints:')
    # for constraint_name in constraints.keys():
    #     print('\t{0}'.format(constraint_name))


    RUN_TIME_EXPERIMENTS = True
    if RUN_TIME_EXPERIMENTS:
        num_runs = 100
        runtimes = np.zeros((num_runs,))
        for i in range(num_runs):
            start_time = time.time()
            solver, variables, constraints = build_scheduling_ilp(num_days, people, set_constraints)
            status = solve_ilp(solver)
            runtimes[i] = time.time() - start_time

        print('Completed {0} runs.'.format(num_runs))
        print('Average execution time: {0:.4f} s'.format(np.mean(runtimes)))
        print('Std. dev.: {0:.4f} s'.format(np.std(runtimes, ddof=1)))

    status = solver.Solve()
    our_status = ORTOOLS_SOLVER_STATUS_TO_OURS_MAP[status]
    print('Status:', our_status)

    print('Objective value =', solver.Objective().Value())

    # print('Solution:')
    # for var_name in variables.keys():
    #     var = variables[var_name]
    #     print('\t{0} = {1}'.format(var_name, var.solution_value()))

    # print('Solution is {0}integral.'.format('' if is_integral(solver) else 'not '))

    if our_status == SolverStatus.OPTIMAL:
        print('Verify solution:', solver.VerifySolution(tolerance=1e-5, log_errors=True))
    elif our_status == SolverStatus.INFEASIBLE:
        print('Infeasible, so will not try to verify solution.')
    else:
        pass