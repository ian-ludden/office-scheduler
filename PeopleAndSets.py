#class definitions for office-scheduler

class SchedulerPrecondError(Exception):
    """
        Error raised when the inputs to one of these clases fails to meet
        the given preconditions
        
        Fields:
            message: explanation of the error.
    """
    def __init__(self, message):
        self.message=message

class Person:
    """ 
        Fields
        uid: string id of person; can be name or other *unique* identifier.
            Initilaized to empty string
        dateList: boolean array where the ith entry is true iff the person can work on 
                  day i.
    """
    
    def __init__(self, uid="",  dateList=[]):
        self.uid = uid
        self.dateList = dateList
            
class SetConstraint:
    """
        Fields
        sid: unique id to identify set. Can be name of dept, project, etc.
        numDays: The number of days that the SetConstraints were built for. Initialized to 0.
        type: the constraint type represented as an integer. 0 if unitiliazed, 1 if a synergy
              constraint, and 2 if a department type constraint
        low_bound: lower bound for the number of people from the set that should be in the office
                   on a given day if a department constraint. Mininum number of days that the entire set
                   should be in the office if a synergy constraint. Initialized to 0
        up_bound: upper bound for the number of people from the set that should be in the office on a
                   given day.  Initialized to numDays. Should only used for deparmtnet constraints, not for
                   synergy constraints. -1 used in constructor to set up_bound to default.
        personList: list of people in the set. Initialized to empty set.
        
    """
    
    def __init__(self, sid="", numDays=0, type=0, personList=[], low_bound=0, up_bound=-1):
        self.sid = sid
        self.numDays = numDays
        
        if type>=0 and type <= 2:
            self.type = type
        else:
            raise SchedulerPrecondError("SetConstraint types should be 0, 1, or 2.")
        
        if low_bound>=0 and up_bound>=0 and low_bound <= numDays and up_bound<= numDays and low_bound <= up_bound:
            self.low_bound=low_bound
            self.up_bound = up_bound
        elif low_bound>=0 and low_bound <= numDays and up_bound==-1:
            self.low_bound=low_bound
            self.up_bound = numDays
        else:
            raise SchedulerPrecondError("lower_bound and upper_bound do not make sense. They are either too small, too large, or upper_bound<lower_bound")
        
        self.personList=personList