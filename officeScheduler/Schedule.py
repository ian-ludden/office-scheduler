# Class definition for representation of a partial/full schedule of shifts
import io
import numpy as np
import officeScheduler.Parser as Parser
import officeScheduler.PeopleAndSets as PAS

class Schedule(object):
	"""
	A Schedule object represents a schedule of shifts, 
	that is, which days/times each employee will work
	during a certain time window.

	Fields:
		n - the number of days/time blocks in the schedule
		people - a list of Person objects (the employees)
		assignments - a len(people) by n numpy array representing each person's shift assignments 
		              (-1 if undecided, 0 if assigned off, 1 if assigned to work)
	"""
	def __init__(self, filepath=None, people=[]):
		if filepath is not None:
			self.buildFromCSV(filepath)

		self.people = people
		self.n = None
		self.assignments = None


	def buildFromCSV(self, filepath):
		"""
		Parses the partial/full schedule stored as a CSV file
		at the given filepath. 
		"""
		# TODO: Implement
		with open(filepath, 'r') as scheduleFile:
			# Reusing Parser.parseCSVs(), but not in the intended way; ok because validation is not yet implemented
			# TODO: Split Parser.parseCSVs() into separate people/set file parsers 
			n, people, setConstraints = Parser.parseCSVs(-1, scheduleFile, [])
		
		if people:
			self.n = len(people[0].dateList)
			self.people = people
			# Initialize all assignments to -1 for undecided
			self.assignments = -1 * np.ones((len(people), self.n))
			for i, person in enumerate(people):
				for j in range(self.n):
					self.assignments[i, j] = int(person.dateList[j])


	def buildFromSolutionVariables(self, variablesDict):
		"""
		Extracts a schedule from a dictionary of problem variable names and their assigned values.
		If self.people is None, then it is populated with Person objects 
		with default names 'Person_1' to 'Person_n'. 
		"""
		# First loop through variables to determine number of people and number of days
		numPeople = 0
		numDays = 0

		for varName in variablesDict.keys():
			if 'Schedule' in varName: # varName looks like 'Schedule_[personIndex]_[dayIndex]'
				nameParts = varName.split('_')
				personIndex = int(nameParts[1])
				dayIndex = int(nameParts[2])
				numPeople = max(numPeople, personIndex)
				numDays = max(numDays, dayIndex)

		# Now that we know how many people & days there are, 
		# we can populate self.n and self.people with defaults
		self.n = numDays

		if not self.people:
			for i in range(numPeople):
				defaultName = 'Person_{0}'.format(i)
				defaultDateList = [True] * self.n
				self.people += PAS.Person(uid=defaultName, dateList=defaultDateList)

		# Initialize self.assignments with correct dimensions
		self.assignments = -1 * np.ones((len(self.people), self.n))

		# Second loop through variables to store assignments
		for varName in variablesDict.keys():
			if 'Schedule' in varName: # varName looks like 'Schedule_[personIndex]_[dayIndex]'
				nameParts = varName.split('_')
				personIndex = int(nameParts[1])
				dayIndex = int(nameParts[2])
				self.assignments[personIndex - 1, dayIndex - 1] = int(variablesDict[varName])


	def __str__(self):
		"""
		Returns a string representation of this schedule.
		"""
		strRepr = ''
		for i, person in enumerate(self.people):
			assignmentsString = ','.join((self.assignments[i,:].astype(int)).astype(str))
			strRepr += '{0},{1}\n'.format(person.uid, assignmentsString)
		return strRepr

		
	def writeToCSV(self, filepath):
		"""
		Writes shift schedule to a CSV file at the given filepath.
		"""
		with open(filepath, 'w') as outputFile:
			outputFile.write(str(self))


	def writeToStringIO(self, stringIOstream):
		"""
		Writes shift schedule to the given StringIO stream.
		"""
		stringIOstream.write(str(self))


if __name__ == '__main__':
	filepath = '../sample_schedule.csv'
	schedule = Schedule(filepath)
	print(schedule)

	schedule.writeToCSV('../sample_schedule_copy.csv')