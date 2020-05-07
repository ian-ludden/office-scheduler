# Class definition for representation of a partial/full schedule of shifts
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
	def __init__(self, filepath=None):
		if filepath is not None:
			self.buildFromCSV(filepath)


	def buildFromCSV(self, filepath):
		"""
		Parses the partial/full schedule stored as a CSV file
		at the given filepath. 
		"""
		# TODO: Implement
		with open(filepath, 'r') as scheduleFile:
			# Reusing Parser.parseCSVs(), but not in the intended way; ok because validation is not yet implemented
			n, people, setConstraints = Parser.parseCSVs(-1, scheduleFile, [])
		
		if people:
			self.n = len(people[0].dateList)
			self.people = people
			# Initialize all assignments to -1 for undecided
			self.assignments = -1 * np.ones((len(people), self.n))
			for i, person in enumerate(people):
				for j in range(len(person.dateList)):
					self.assignments[i, j] = int(person.dateList[j])


	def buildFromPulpVariables(self, variables):
		"""
		Extracts a schedule from the variables of a PuLP linear program.
		"""
		# TODO: implement
		pass


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


if __name__ == '__main__':
	filepath = '../sample_schedule.csv'
	schedule = Schedule(filepath)
	print(schedule)

	schedule.writeToCSV('../sample_schedule_copy.csv')