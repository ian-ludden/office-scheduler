#class definitions for office-scheduler

class SchedulerClassConstError(Exception):
    """
        Error raised when the inputs to one of these clases fails to meet
            meet the guarantees (e.g. low_bound should be <= up_bound)
        
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
        type: the constraint type represented as an integer. 0 if unitiliazed, 1 if a synergy
              constraint, and 2 if a department type constraint
        low_bound: lower bound for the number of people from the set that should be in the office
                   on a given day if a department constraint. Mininum number of days that the entire set
                   should be in the office if a synergy constraint. Initialized to 0
        up_bound: upper bound for the number of people from the set that should be in the office on a
                   given day.  Initialized to -1, which is the stand in value for infinity.
                   Should only used for deparmtnet constraints, not for synergy constraints.
        personList: list of people in the set. Initialized to empty set.
        
    """
    
    def __init__(self, sid="", type=0, personList=[], low_bound=0, up_bound=-1):
        self.sid = sid        
        if type>=0 and type <= 2:
            self.type = type
        else:
            raise SchedulerPrecondError("SetConstraint types should be 0, 1, or 2.")
        
        if low_bound>=0 and (low_bound <= up_bound or up_bound == -1):
            self.low_bound=low_bound
            self.up_bound = up_bound
        else:
            raise SchedulerPrecondError("lower_bound and upper_bound do not make sense. They are either too small, too large, or upper_bound<lower_bound")
        
        self.personList=personList