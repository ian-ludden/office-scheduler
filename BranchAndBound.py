# Time-constrained DFS branch-and-bound implementation
from multiprocessing import Process
import pulp as pl
import sys

import PeopleAndSets as PAS
import Parser


class BranchAndBoundManager(object):
	"""A BranchAndBoundManager optimizes a given LP 
	   using time-constrained DFS branch-and-bound.
	   Fields
		problem: A PuLP LpProblem
		timeLimit: max time, in seconds, to run the algorithm; default is 60 seconds
		LB: lower bound on opt value of integer solution to LP; 
			initialized to 0 since we are maximizing a nonnegative function
		best: global best solution found so far
	"""
	def __init__(self, problem, timeLimit=60):
		super(BranchAndBoundManager, self).__init__()
		self.problem = problem
		self.timeLimit = timeLimit
		self.LB = 0
		self.best = None

		# Start running branch-and-bound and block for timeLimit seconds
		# bnbProcess = Process(target=self.dfsBranchAndBound)
		# bnbProcess.start()
		# bnbProcess.join(timeout=self.timeLimit)

		# # Terminate if branch-and-bound takes too long
		# bnbProcess.terminate()

		# TODO: figure out how to implement time limit
		# (above approach modifies self.LB and self.best in a different thread)

		self.dfsBranchAndBound()


	def dfsBranchAndBound(self):
		"""
		Iterative implementation of branch-and-bound via depth-first search.
		"""
		# For now, just solve the LP directly
		# TODO: actually implement branch-and-bound
		result = self.problem.solve()
		if pl.LpStatus[result] == 'Optimal':
			print('Solved to optimality!')
			print('Objective value: ', pl.value(self.problem.objective))
			for variable in self.problem.variables():
					print('{0} = {1}'.format(variable.name, variable.varValue))
			self.LB = pl.value(self.problem.objective)
			self.best = [x_ij.value() for x_ij in self.problem.variables()]
		else:
			print('Failed to solve: status {0}'.format(pl.LpStatus[result]))

		# Branch-and-bound for finding integer solution to problem p2
		# (a bit different from our problem since variables non-binary)

		# def possibleVals(variableName):
		#	 if variableName == 'x':
		#		 return [0, 1, 2, 3, 4]
		#	 elif variableName == 'y':
		#		 return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
		#	 elif variableName == 'z':
		#		 return [0, 1, 2, 3, 4, 5, 6, 7]
		#	 else:
		#		 return []

		# fixedVars = [] # List of fixed variables 
		# fixedVarNames = [] # List of their names
		# fixedVals = [] # List of their values

		# iterationCount = 0
		# B = 100000 # Trivial upper bound
		# bestSoln = None

		# stack = LifoQueue()
		# root = Node(p2, fixedVars, fixedVarNames, fixedVals, '')
		# stack.put(root)

		# while not stack.empty():
		# 	node = stack.get()
		# 	iterationCount += 1
		# 	if iterationCount % 100 == 0:
		# 		print(iterationCount)
				
		# 	print(node.nodeStr)
		# 	print(node.fixedVarNames)
		# 	print(node.fixedVals)
			
		# 	status = node.problem.solve()
		# 	if pl.LpStatus[status] is 'Optimal':
		# 		xVal = pl.value(x)
		# 		yVal = pl.value(y)
		# 		zVal = pl.value(z)
		# 		# If solution is integral, then it may update upper bound
		# 		if xVal == int(xVal) and yVal == int(yVal) and zVal == int(zVal):
		# 			objVal = pl.value(node.problem.objective)
		# 			if objVal < B:
		# 				bestSoln = [xVal, yVal, zVal]
		# 				B = objVal
		# 				print('Improved bound: B =', B)
			
		# 	# Create candidate child nodes
		# 	for var in node.problem.variables():
		# 		if var.name not in node.fixedVarNames:
		# 			for val in possibleVals(var.name):
		# 				# Solve LP relaxation to get lower bound
		# 				child_node = Node(node.problem, node.fixedVars + [var], node.fixedVarNames + [var.name], node.fixedVals + [val], node.nodeStr + ', {0} = {1}'.format(var.name, val))
		# 				child_lb = child_node.lowerBound()
		# #				 if child_lb is None:
		# #					 print('Fix {0} = {1:d}, lb = {2}'.format(var.name, val, child_lb))
		# #				 else:
		# #					 print('Fix {0} = {1:d}, lb = {2:.3f}'.format(var.name, val, child_lb))
		# 				if child_lb is not None and child_lb <= B:
		# 					stack.put(child_node)
			
		# print('Terminated after {0} iterations.'.format(iterationCount))
		# print('Optimal integer solution:', bestSoln)
		# print('Optimal value:', B)

		# lpOpt = prob.solve()

		# pass

class Node(object):
	"""
		Represents a node in the branch-and-bound tree.

	   	Fields:
		problem: a PuLP LpProblem
		fixedVars: list of LpVariable objects with fixed values
		fixedVarNames: list of names of fixedVars
		fixedVals: list of values of fixedVars
		nodeStr: a string description of this node
	"""
	def __init__(self, problem, fixedVars, fixedVarNames, fixedVals, nodeStr):
		super(Node, self).__init__()
		self.problem = problem.copy()
		self.fixedVars = fixedVars
		self.fixedVarNames = fixedVarNames
		self.fixedVals = fixedVals
		self.nodeStr = nodeStr
		
		if len(fixedVars) > 0:
			# Only the last fixed variable is new
			self.problem += fixedVars[-1] == fixedVals[-1]


	def lowerBound(self):
		"""Solve LP relaxation to get lower bound.
		   Returns False if infeasible."""
		status = self.problem.solve()
		if pl.LpStatus[status] is 'Optimal':
			return pl.value(self.problem.objective)
		else:
			return None


def buildSchedulingLP(numDays, people, setConstraints):
	"""
	Given outputs of Parser.parseCSVs(), 
	constructs a PuLP LpProblem representing the scheduling problem.
	"""
	prob = pl.LpProblem('Office Scheduling Problem', pl.LpMinimize)

	# Ranges for iterating through people, sets, and days
	PEOPLE = range(1, len(people) + 1)
	SETS = range(1, len(setConstraints) + 1) # TODO: consider deleting, may not need
	DAYS = range(1, numDays + 1)

	# Create decision variables x_{i,j} indicating whether person i is scheduled on day j
	x = pl.LpVariable.dicts('Schedule', (PEOPLE, DAYS), cat='Binary')
	# TODO: should cat be continuous, since we want to solve LP relaxation to find lower bound(s)? 

	# Add objective: negated sum of all x_{i,j}
	prob += -1 * pl.lpSum(x)

	# Copy people UIDs to list for building set constraints
	personUIDs = [person.uid for person in people]

	# Add constraints for each person's availability:
	# Person i can only be scheduled on day j if their dateList entry for day j is True
	for i in PEOPLE:
		for j in DAYS:
			availability = int(people[i - 1].dateList[j - 1])
			prob += x[i][j] <= availability, '{0} {1} work on day {2}.'.format(people[i - 1].uid, 'can' if availability == 1 else 'can\'t', j)

	for setConstraint in setConstraints:
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
			# TODO: implement
			pass

		else:
			pass
			# # Should never reach this case due to type validation in SetConstraint.__init__()
			# # Wait... Could reach this case if up_bound is -1 for a DEPARTMENT-type constraint
			# print('Ignoring unsupported set constraint: sid = {0}, type = {1}.'.format(setConstraint.sid, setConstraint.constraintType))

	return prob


if __name__ == '__main__':
	# TODO: create/read sample input files
	defaultNumDays = 10 # Two weeks of M-F
	peopleFname = 'sample_employees.csv'
	setsFname = 'sample_set_constraints.csv'

	with open(peopleFname, 'r') as people_file:
		with open(setsFname, 'r') as sets_file:
			numDays, people, setConstraints = Parser.parseCSVs(n=defaultNumDays, peopleFile=people_file, setFile=sets_file)

	schedProb = buildSchedulingLP(numDays, people, setConstraints)
	print(schedProb)

	bnbManager = BranchAndBoundManager(problem=schedProb, timeLimit=4)

	varNames = [var.name for var in schedProb.variables()]

	print('Best objective value: ', bnbManager.LB)
	print('This means we can schedule {0:d} person-days with the following assignments:'.format(int(-1 * bnbManager.LB)))
	

	for i, person in enumerate(people, start=1):
		sys.stdout.write('{0},'.format(person.uid))
		for j in range(1, numDays + 1):
			lpVarName = 'Schedule_{0}_{1}'.format(i, j)
			lpVar = schedProb.variables()[varNames.index(lpVarName)]
			sys.stdout.write('{0},'.format(int(lpVar.value())))
		print() # new line