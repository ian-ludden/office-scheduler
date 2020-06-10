import argparse
import numpy as np
import time

from ortools_utils import (build_scheduling_ilp, solve_ilp, 
    extract_solution, ORTOOLS_SOLVER_STATUS_TO_OURS_MAP)
import Parser
from Solver import Solver, SolverStatus
from Schedule import Schedule


DEBUG_PRINT = True


class DirectILPSolver(Solver):
    """docstring for DirectILPSolver"""
    def __init__(self, people, set_constraints, time_limit=-1):
        super(DirectILPSolver, self).__init__(people, set_constraints, time_limit)
        self.num_days = -1
        if people:
            self.num_days = len(people[0].dateList)


    def solve(self):
        solver, variables, constraints = build_scheduling_ilp(self.num_days, self.people, self.set_constraints)

        if DEBUG_PRINT:
            print('No. variables:', solver.NumVariables())
            print('No. constraints:', solver.NumConstraints())

        if self.time_limit > 0:
            solver.SetTimeLimit(time_limit)
        
        status = solver.Solve()
        self.status = ORTOOLS_SOLVER_STATUS_TO_OURS_MAP[status]

        if DEBUG_PRINT:
            print('Status:', self.status)
            print('Objective value =', solver.Objective().Value())

        solution_dict = extract_solution(solver)
        best_schedule = Schedule(people=self.people)
        best_schedule.buildFromSolutionVariables(solution_dict)

        if DEBUG_PRINT:
        	print('Schedule:\n{0}'.format(best_schedule))

        return best_schedule


if __name__ == '__main__':
    commandLineParser = argparse.ArgumentParser(description='Takes an integer and two csv files and parses them for the office scheduler')
    commandLineParser.add_argument('numdays', type=int, help="the total number of days to schedule for")
    commandLineParser.add_argument('peopleFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the people being scheduled")
    commandLineParser.add_argument('setFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the department and synergy constraints")

    args = commandLineParser.parse_args()

    num_days, people, set_constraints = Parser.parseCSVs(n=args.numdays, peopleFile=args.peopleFile, setFile=args.setFile)
    time_limit = 5 # seconds

    #TODO: currently converting dictionary to list; should evetually change to actually use the dictionary
    people=list(people.values())
    set_constraints=list(set_constraints.values())

    solver = DirectILPSolver(people, set_constraints, time_limit)

    schedule = solver.solve()


    RUN_TIME_EXPERIMENTS = False
    if RUN_TIME_EXPERIMENTS:
        num_runs = 100
        runtimes = np.zeros((num_runs,))
        for i in range(num_runs):
            start_time = time.time()
            solver = DirectILPSolver(people, set_constraints, time_limit)
            schedule = solver.solve()
            runtimes[i] = time.time() - start_time

        print('Completed {0} runs.'.format(num_runs))
        print('Average execution time: {0:.4f} s'.format(np.mean(runtimes)))
        print('Std. dev.: {0:.4f} s'.format(np.std(runtimes, ddof=1)))
