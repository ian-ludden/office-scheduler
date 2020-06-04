# Utilities for solving office scheduling problem with PuLP package
import argparse
import pulp as pl

import time

from PeopleAndSets import SetConstraintType
import Parser

SCHEDULE_VAR_PREFIX = 'Schedule'
SYNERGY_VAR_PREFIX = 'Synergy'

def build_scheduling_lp(num_days, people, set_constraints):
    """
    Given outputs of Parser.parseCSVs(), 
    constructs a PuLP LpProblem representing the scheduling problem.
    The objective is to maximize the number of person-days. 
    """
    prob = pl.LpProblem('Office_Scheduling_Problem', pl.LpMaximize)

    # Find indices of 'synergy' set constraints
    synergy_indices = []
    for index, set_constraint in enumerate(set_constraints):
        if set_constraint.constraintType.value == SetConstraintType.SYNERGY.value:
            synergy_indices.append(index)

    # Ranges for iterating through people, all sets, synergy sets, and days
    PEOPLE = range(1, len(people) + 1)
    PEOPLE = [person.uid for person in people]
    SYNERGY_SETS = [set_constraints[i].sid for i in synergy_indices]
    DAYS = range(1, num_days + 1)

    # Create relaxed decision variables x_{i,j} indicating whether person i is scheduled on day j
    x = pl.LpVariable.dicts(SCHEDULE_VAR_PREFIX, (PEOPLE, DAYS), lowBound=0, upBound=1, cat='Continuous')

    # Create relaxed decision variables y_{k,j} indicating whether team k is all present on day j
    y = pl.LpVariable.dicts(SYNERGY_VAR_PREFIX, (SYNERGY_SETS, DAYS), lowBound=0, upBound=1, cat='Continuous')

    # Add objective: sum of all x_{i,j}
    prob += 1 * pl.lpSum(x)

    # Add constraints for each person's availability:
    # Person i can only be scheduled on day j if their dateList entry for day j is True
    for person in people:
        for j in DAYS:
            availability = int(person.dateList[j - 1])
            if availability == 0:
                prob += x[person.uid][j] <= availability, '{0} can\'t work on day {1}.'.format(person.uid, j)

    for index, set_constraint in enumerate(set_constraints):
        if set_constraint.constraintType.value == SetConstraintType.DEPARTMENT.value:
            # Add upper-bound constraint for each day
            if set_constraint.up_bound > -1:
                for j in DAYS:
                    prob += pl.lpSum([x[person_uid][j] for person_uid in set_constraint.personList]) <= set_constraint.up_bound, '{0}_UB_day_{1}'.format(set_constraint.sid, j)

            # Add lower-bound constraint for each day
            for j in DAYS:
                prob += pl.lpSum([x[person_uid][j] for person_uid in set_constraint.personList]) >= set_constraint.low_bound, '{0}_LB_day_{1}'.format(set_constraint.sid, j)

        elif set_constraint.constraintType.value == SetConstraintType.SYNERGY.value:
            # Add lower-bound constraint for number of days with full set present
            prob += pl.lpSum(y[set_constraint.sid][j] for j in DAYS) >= set_constraint.low_bound, 'Team {0} all present at least {1} days'.format(set_constraint.sid, set_constraint.low_bound)

            # Add constraint to enforce all of set k showing up when y_{k,j} is 1
            for j in DAYS:
                prob += pl.lpSum(x[person_uid][j] for person_uid in set_constraint.personList) >= len(set_constraint.personList) * y[set_constraint.sid][j], 'Team {0} all present on day {1} if assigned to be'.format(set_constraint.sid, j)
        
        else:
            raise Exception('Invalid constraintType field for set constraint with id {0}:\n\t{1}'.format(set_constraint.sid, set_constraint.constraintType))
            pass
            # # Should never reach this case due to type validation in SetConstraint.__init__()
            # # Wait... Could reach this case if up_bound is -1 for a DEPARTMENT-type constraint
            # print('Ignoring unsupported set constraint: sid = {0}, type = {1}.'.format(set_constraint.sid, set_constraint.constraintType))

    print(prob)
    return prob


def solve_lp(problem):
    """
    Solves the given LP relaxation and returns the PuLP solver status code. 
    """
    result = problem.solve()
    return pl.LpStatus[result]


def is_integral(problem):
    """
    Returns True if all variables in the current solution 
    to the given LP relaxation are integral; False otherwise.
    """
    for var in problem.variables():
        if not (var.value() == int(var.value())):
            return False

    return True


def extract_solution(problem):
    """
    Extracts the solution to the given problem, 
    if it has been solved, 
    returning a dictionary of variable names to values. 
    Returns None if the problem is not solved. 
    """
    if pl.LpStatus[problem.status] == 'Not Solved':
        return None

    solution = {}
    for var in problem.variables():
        solution[var.name] = var.value()

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

    lp = build_scheduling_lp(num_days, people, set_constraints)

    import pdb; pdb.set_trace()

    status = solve_lp(lp)
    print('Status:', status)

    if status == 'Optimal':
        print('Solution is {0}integral.'.format('' if is_integral(lp) else 'not '))
