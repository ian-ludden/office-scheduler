# Time-constrained solver for shift scheduling IP
from multiprocessing import Process, Manager
import pulp as pl
import sys

import officeScheduler.PeopleAndSets as PAS
import officeScheduler.Parser as Parser


class SolverManager(object):
	"""
	A SolverManager optimizes a given integer programming formulation of
	a shift scheduling problem. 
	
	Fields:
		problem - A PuLP LpProblem
		timeLimit - max time, in seconds, to run the algorithm; default is 60 seconds
		optValue - optimal value found; initially 0 since our objective is nonnegative
		optSolution - optimal variable assignments found; initially None
		status - status of LP solver ('Optimal', 'Not Solved', 'Infeasible', 'Unbounded', or 'Undefined')
	"""
	def __init__(self, problem, timeLimit=60):
		super(SolverManager, self).__init__()
		self.problem = problem
		self.timeLimit = timeLimit
		self.optValue = 0
		self.optSolution = None
		self.status = None

		# Run PuLP solver as a separate process to enforce time limit
		taskManager = Manager()
		returnDict = taskManager.dict()
		solverProcess = Process(target=solveIP, args=(self.problem, returnDict))
		solverProcess.start()
		solverProcess.join(timeout=self.timeLimit)

		# Terminate if solver takes too long
		solverProcess.terminate()

		# Update optimal value and solution if solver finished
		if 'optValue' in returnDict.keys():
			self.optValue = returnDict['optValue']
		if 'optSolution' in returnDict.keys():
			self.optSolution = returnDict['optSolution']
		if 'status' in returnDict.keys():
			self.status = returnDict['status']


def solveIP(problem, returnDict):
	"""
	Runs PuLP with its default solver (CBC) to solve the given IP. 

	The optimal objective value and variable assignments are stored in 
	the given returnDict dictionary.
	"""
	result = problem.solve()
	if pl.LpStatus[result] == 'Optimal':
		returnDict['optValue'] = pl.value(problem.objective)
		returnDict['optSolution'] = [x_ij.value() for x_ij in problem.variables()]
		return
	else:
		returnDict['status'] = pl.LpStatus[result]


def buildSchedulingLP(numDays, people, setConstraints):
	"""
	Given outputs of Parser.parseCSVs(), 
	constructs a PuLP LpProblem representing the scheduling problem.
	The objective is to maximize the number of person-days. 
	"""
	prob = pl.LpProblem('Office Scheduling Problem', pl.LpMaximize)

	# Find indices of 'synergy' set constraints
	synergyIndices = []
	for index, setConstraint in enumerate(setConstraints):
		if setConstraint.constraintType is PAS.SetConstraintType.SYNERGY:
			synergyIndices.append(index)

	# Ranges for iterating through people, all sets, synergy sets, and days
	PEOPLE = range(1, len(people) + 1)
	SETS = range(1, len(setConstraints) + 1) # TODO: consider deleting, may not need
	SYNERGY_SETS = (1, len(synergyIndices) + 1)
	DAYS = range(1, numDays + 1)


	# Create decision variables x_{i,j} indicating whether person i is scheduled on day j
	x = pl.LpVariable.dicts('Schedule', (PEOPLE, DAYS), cat='Binary')

	# Create decision variables y_{k,j} indicating whether team k is all present on day j
	y = pl.LpVariable.dicts('AllTeam', (SYNERGY_SETS, DAYS), cat='Binary')

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

	print(schedProb)

	solverManager = SolverManager(problem=schedProb, timeLimit=timeLimit)

	if solverManager.optSolution is None:
		print('Failed to solve. Status:', solverManager.status)
		if solverManager.status == 'Undefined':
			print('(Likely, time limit exceeded.)')
		exit(0)

	print('Best objective value: ', solverManager.optValue)
	print('The following schedule achieves {0:d} person-days:'.format(int(solverManager.optValue)))
	
	bestScheduleFound = solverManager.optSolution

	# Print schedule; TODO: make this a function, perhaps for a "Schedule" class
	for i, person in enumerate(people, start=1):
		sys.stdout.write('{0},'.format(person.uid))
		for j in range(1, numDays + 1):
			lpVarName = 'Schedule_{0}_{1}'.format(i, j)
			lpVarValue = bestScheduleFound[varNames.index(lpVarName)]
			if lpVarValue is None:
				import pdb; pdb.set_trace()
			else:
				sys.stdout.write('{0},'.format(int(lpVarValue)))
		print()


if __name__ == '__main__':
	defaultNumDays = 10 # Two weeks of M-F
	peopleFname = '../sample_employees.csv'
	setsFname = '../sample_set_constraints.csv'

	with open(peopleFname, 'r') as people_file:
		with open(setsFname, 'r') as sets_file:
			numDays, people, setConstraints = Parser.parseCSVs(n=defaultNumDays, peopleFile=people_file, setFile=sets_file)

	optimizeSchedule(numDays, people, setConstraints, timeLimit=5)