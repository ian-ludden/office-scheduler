# Class definition for representation of a partial/full schedule of shifts
import io
import numpy as np
import pulp as pl

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
		raise NotImplementedError('This function has not yet been implemented.')
		# with open(filepath, 'r') as scheduleFile:
		# 	# Reusing Parser.parseCSVs(), but not in the intended way; ok because validation is not yet implemented
		# 	# TODO: Split Parser.parseCSVs() into separate people/set file parsers 
		# 	n, people, setConstraints = Parser.parseCSVs(-1, scheduleFile, [])


	def buildFromSolutionVariables(self, variablesDict):
		"""
		Extracts a schedule from a dictionary of problem variable names and their assigned values.
		If self.people is empty, then it is populated with Person objects 
		with default names 'Person_1' to 'Person_n'. 
		"""
		# First loop through variables to determine number of people and number of days
		num_days = 0
		person_uids = []

		if variablesDict is None:
			self.assignments = -1 * np.ones((max(len(self.people), 10), 10))
			return

		for varName in variablesDict.keys():
			if 'Schedule' in varName: # varName looks like 'Schedule_[person_uid]_[day_index]'
				name_parts = varName.split('_')
				person_uid = name_parts[1]
				if person_uid not in person_uids:
					person_uids.append(person_uid)
				day_index = int(name_parts[2])
				num_days = max(num_days, day_index)

		num_people = len(person_uids)

		# Now that we know how many people & days there are, 
		# we can populate self.n and self.people with defaults
		self.n = num_days

		if not self.people:
			for i in range(num_people):
				defaultName = 'Person_{0}'.format(i)
				defaultDateList = [True] * self.n
				self.people += PAS.Person(uid=defaultName, dateList=defaultDateList)
		else: 
			# Update person_uids with uids from self.people in the correct order
			person_uids = []
			for person in self.people:
				person_uids.append(person.uid)

		# Initialize self.assignments with correct dimensions
		self.assignments = -1 * np.ones((len(self.people), self.n))

		# Second loop through variables to store assignments
		for varName in variablesDict.keys():
			if 'Schedule' in varName: # varName looks like 'Schedule_[person_uid]_[day_index]'
				name_parts = varName.split('_')
				person_uid = name_parts[1]
				day_index = int(name_parts[2])
				self.assignments[person_uids.index(person_uid), day_index - 1] = int(variablesDict[varName])


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

	schedule2 = Schedule()
	schedule2.buildFromCSV('../sample_schedule_copy.csv')