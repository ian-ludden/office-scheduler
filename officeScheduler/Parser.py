"""
File parser for office scheduler.
Takes as an input a number n and 2 csv files people.csv and setConstraints.csv

Each line in people.csv should have the format:
uid,True (1) if person can work on day 1, True if person can work on day 2, ... , True if person can work on day n
For example, if we look at a single work week and Sarah can work M, W, and F then n should be fine and
Sarah,1,0,1,0,1
should be aline in people.csv

A line in the setConstraints file has the general format
set_id, constraintType, low_bound, (up_bound), list of people in set
There are 2 types of set contraints.
The first, departmental (or type 1 constraints), let you specify a 
    min and a max number of people from the deparment 
If Sarah, John, and Ellie work in sales and you want at least one
    and no more than two people from sales on any given day, the 
    setConstraints file should contain:
sales,1,1,2,Sarah,John,Ellie
If there is no upper bound, you can use -1 in place of up_bound.
low_bound should always be at least 0.

The second type of contraints, synergy constraints, let you specify
    a set of people that you want in the office together for at least
    x total days.
For these constraints, there should be no entry for up_bound.
If you want Ellie and John to be in the office together for at
    least 2 of the 5 days to work on their paper project, then
    setContraints.csv should contain the line
paperProject,2,Ellie,John
"""

import officeScheduler.PeopleAndSets as PAS
import argparse

def parseCSVs(n, peopleFile, setFile):
    """
    Arguments:
        n - number of days to consider. Each line of peopleFile should have n+1 entries
        peopleFile - a file to read people lines from (not the name of the file, the actual file object)
        setFile - a file to read set constraints from (not the name of the file, the actual file object)
        
     Returns tuple of form (n, [list of People objects], [list of SetConstraint objects]
    """
    
    #TODO: need to trim extra commas and stuff like that.
    #TODO: consider people and setConstraints as dictionaries indexed by uid and sid for easier lookup
    #   alternatively, add person object to set contraint instead of just person's id.
    #   Can also only store people as a dictionary to facilitate this better.
    #   On the other hand, lists make for easier time converting from lists to indexed IP variables
    #   Maybe store as tuple (personIndex, personObject) in people list in SetConstraint or something.
    #   Or can create a dictionary to map from person name to index in people.
    
    setConstraints = {}
    for line in setFile:
        line = line.strip()
        line = line.split(',')
        #TODO: check that line is correct length, throw exception otherwise
        sid=line[0]
        setType = int(line[1])
        if setType==1:
            low_bound = int(line[2])
            up_bound=int(line[3])
        else:
            low_bound=int(line[2])
            up_bound=-1
        peopleList = []    
        setConstraints[sid] = (PAS.SetConstraint(sid, PAS.SetConstraintType(setType), peopleList, low_bound, up_bound))
    
    people = {}
    for line in peopleFile:
        line = line.strip()
        line = line.split(',')
        #TODO: check that line is correct length, throw exception otherwise
        uid=line[0]
        dates = line[1:n+1]
        dates = [True if c=='1' else False for c in dates]
        for s in line[n+1:]:
            setConstraints[s].personList.append(uid)
        #TODO: should probably throw an exception if not 0 or 1.
        #TODO: Also throw exception of uid is not unique
        people[uid] = PAS.Person(uid, dates)

    return (n, people, setConstraints)

"""
Main = reads command line arguments to pass to parseCSV, opens the two csv files,
and passes all arguments to parseCSV, printing the output (for debuggin purposes.
"""
if __name__ == "__main__":
    commandLineParser = argparse.ArgumentParser(description='Takes an integer and two csv files and parses them for the office scheduler')
    commandLineParser.add_argument('numdays', type=int, help="the total number of days to schedule for")
    commandLineParser.add_argument('peopleFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the people being scheduled")
    commandLineParser.add_argument('setFile', type=argparse.FileType('r', encoding='utf8'), help="A csv file specifying all of the department and synergy constraints")
    
    args = commandLineParser.parse_args()    
    n, people, sets = parseCSVs(args.numdays,args.peopleFile,args.setFile)
    print(n)
    
    for person in people.values():
        print(person.uid, person.dateList)
    for setC in sets.values():
        print(setC.sid, setC.constraintType, setC.low_bound, setC.up_bound, setC.personList)