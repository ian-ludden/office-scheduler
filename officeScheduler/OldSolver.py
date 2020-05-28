# Time-constrained solver for shift scheduling IP
import argparse
from multiprocessing import Process, Manager
import pulp as pl
import sys

import officeScheduler.PeopleAndSets as PAS
import officeScheduler.Parser as Parser
from officeScheduler.Schedule import Schedule


# TODO: redesign so Solver is a superclass of specific solver implementations


class SolverManager(object):
	"""
	A SolverManager optimizes a given integer programming formulation of
	a shift scheduling problem. 
	
	Fields:
		problem - A PuLP LpProblem
		timeLimit - max time, in seconds, to run the algorithm; default is 60 seconds; -1 means no time limit
		optValue - optimal value found; initially 0 since our objective is nonnegative
		optSolution - optimal variable assignments found (dictionary of names to values); initially None
		status - status of LP solver ('Optimal', 'Not Solved', 'Infeasible', 'Unbounded', or 'Undefined')
	"""
	def __init__(self, problem, timeLimit=60):
		super(SolverManager, self).__init__()
		self.problem = problem
		self.timeLimit = timeLimit
		self.optValue = 0
		self.optSolution = None
		self.status = None

		if self.timeLimit > 0:
			# Run PuLP solver as a separate process to enforce time limit
			taskManager = Manager()
			returnDict = taskManager.dict()
			solverProcess = Process(target=solveIP, args=(self.problem, returnDict))
			solverProcess.start()
			solverProcess.join(timeout=self.timeLimit)

			# Terminate if solver takes too long
			solverProcess.terminate()
		else:
			# Solve with no time limit
			returnDict = {}
			solveIP(self.problem, returnDict)

		# Update optimal value and solution if solver finished
		if 'optValue' in returnDict.keys():
			self.optValue = returnDict['optValue']
		if 'optSolution' in returnDict.keys():
			self.optSolution = returnDict['optSolution']
		if 'status' in returnDict.keys():
			self.status = returnDict['status']


class SolverTimeoutError(Exception):
	"""
	Error raised when the solver exceeds the specified time limit.
		
	Fields:
		message - explanation of the error
	"""
	def __init__(self, message='Time limit exceeded.'):
		super(SolverTimeoutError, self).__init__()
		self.message=message


class SolverFailureError(Exception):
	"""
	Error raised when the solver fails in some other way (not time limit exceeded).
		
	Fields:
		message - explanation of the error
	"""
	def __init__(self, message='Unknown solver error.'):
		super(SolverFailureError, self).__init__()
		self.message=message


def solveIP(problem, returnDict):
	"""
	Runs PuLP with its default solver (CBC) to solve the given IP. 

	The optimal objective value and variable assignments are stored in 
	the given returnDict dictionary.
	"""
	try:
		result = problem.solve()
	except Exception as e:
		print(e)
		raise e

	if pl.LpStatus[result] == 'Optimal':
		optSolutionDict = {}
		for x_ij in problem.variables():
			optSolutionDict[x_ij.name] = x_ij.value()
		returnDict['optSolution'] = optSolutionDict

	if pl.LpStatus[result] == 'Undefined':
		pass # TODO: Handle somehow?
	
	returnDict['status'] = pl.LpStatus[result]
	returnDict['optValue'] = pl.value(problem.objective)


def buildSchedulingLP(numDays, people, setConstraints):
	"""
	Given outputs of Parser.parseCSVs(), 
	constructs a PuLP LpProblem representing the scheduling problem.
	The objective is to maximize the number of person-days. 
	"""
	prob = pl.LpProblem('Office_Scheduling_Problem', pl.LpMaximize)

	# Find indices of 'synergy' set constraints
	synergyIndices = []
	for index, setConstraint in enumerate(setConstraints):
		if setConstraint.constraintType is PAS.SetConstraintType.SYNERGY:
			synergyIndices.append(index)

	# Ranges for iterating through people, all sets, synergy sets, and days
	PEOPLE = range(1, len(people) + 1)
	SETS = range(1, len(setConstraints) + 1) # TODO: consider deleting, may not need
	SYNERGY_SETS = range(1, len(synergyIndices) + 1)
	DAYS = range(1, numDays + 1)


	# Create decision variables x_{i,j} indicating whether person i is scheduled on day j
	x = pl.LpVariable.dicts('Schedule', (PEOPLE, DAYS), lowBound=0, upBound=1, cat='Continuous')

	# Create decision variables y_{k,j} indicating whether team k is all present on day j
	y = pl.LpVariable.dicts('AllTeam', (SYNERGY_SETS, DAYS), lowBound=0, upBound=1, cat='Continuous')

	# Add objective: sum of all x_{i,j}
	prob += 1 * pl.lpSum(x)

	# Copy people UIDs to list for building set constraints
	personUIDs = [person.uid for person in people]

	# Add constraints for each person's availability:
	# Person i can only be scheduled on day j if their dateList entry for day j is True
	for i in PEOPLE:
		for j in DAYS:
			availability = int(people[i - 1].dateList[j - 1])
			prob += x[i][j] <= availability, '{0} {1} work on day {2}.'.format(people[i - 1].uid, 'can' if availability == 1 else 'can\'t', j)

	for index, setConstraint in enumerate(setConstraints):
		# Convert setConstraint.personList to list of 1-based indices for LP variables
		peopleIndices = []
		for personUID in setConstraint.personList:
			peopleIndices.append(personUIDs.index(personUID) + 1)

		if setConstraint.constraintType is PAS.SetConstraintType.DEPARTMENT and setConstraint.up_bound > -1:
			# Add upper-bound constraint for each day
			for j in DAYS:
				prob += pl.lpSum([x[i][j] for i in peopleIndices]) <= setConstraint.up_bound, 'Set {0} UB for day {1}'.format(setConstraint.sid, j)

			# Add lower-bound constraint for each day
			for j in DAYS:
				prob += pl.lpSum([x[i][j] for i in peopleIndices]) >= setConstraint.low_bound, 'Set {0} LB for day {1}'.format(setConstraint.sid, j)

		elif setConstraint.constraintType is PAS.SetConstraintType.SYNERGY:
			# Add lower-bound constraint for number of days with full set present
			k = synergyIndices.index(index) + 1
			prob += pl.lpSum(y[k][j] for j in DAYS) >= setConstraint.low_bound, 'Team {0} all present at least {1} days'.format(setConstraint.sid, setConstraint.low_bound)

			# Add constraint to enforce all of set k showing up when y_{k,j} is 1
			for j in DAYS:
				prob += pl.lpSum(x[i][j] for i in peopleIndices) >= len(peopleIndices) * y[k][j], 'Team {0} all present on day {1} if assigned to be'.format(setConstraint.sid, j)
		
		else:
			pass
			# # Should never reach this case due to type validation in SetConstraint.__init__()
			# # Wait... Could reach this case if up_bound is -1 for a DEPARTMENT-type constraint
			# print('Ignoring unsupported set constraint: sid = {0}, type = {1}.'.format(setConstraint.sid, setConstraint.constraintType))

	return prob


def optimizeSchedule(numDays, people, setConstraints, timeLimit):
	"""
	Constructs the scheduling IP and attempts to solve with PuLP 
	within the given time limit.
	"""
	schedProb = buildSchedulingLP(numDays, people, setConstraints)
	varNames = [var.name for var in schedProb.variables()]

	# print(schedProb)

	solverManager = SolverManager(problem=schedProb, timeLimit=timeLimit)

	if solverManager.status is None:
		raise SolverTimeoutError() # TODO: This may not be true. Other errors can cause status to be None.
	elif solverManager.status != 'Optimal':
		import pdb; pdb.set_trace()
		raise SolverFailureError('Solver failed with status \'{0}\'.'.format(solverManager.status))

	print('Best objective value: ', int(solverManager.optValue))
	print('The following schedule achieves {0:d} person-days:'.format(int(solverManager.optValue)))

	optSchedule = Schedule(people=people)
	optSchedule.buildFromSolutionVariables(solverManager.optSolution)
	return optSchedule


if __name__ == '__main__':
	commandLineParser = argparse.ArgumentParser(description='Takes an integer and two csv files and parses them for the office scheduler')
	commandLineParser.add_argument('numdays', type=int, help="the total number of days to schedule for")
	commandLineParser.add_argument('peopleFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the people being scheduled")
	commandLineParser.add_argument('setFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the department and synergy constraints")

	args = commandLineParser.parse_args()

	numDays, people, setConstraints = Parser.parseCSVs(n=args.numdays, peopleFile=args.peopleFile, setFile=args.setFile)

	try:
		timeLimit = 10 # seconds
		sched = optimizeSchedule(numDays, people, setConstraints, timeLimit=timeLimit)
		print(sched)
		sched.writeToCSV('../output_schedule.csv')

	except Exception as e:
		print(sys.exc_info()[0], e.message)
