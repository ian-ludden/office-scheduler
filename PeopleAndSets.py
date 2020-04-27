#class definitions for office-scheduler
from enum import Enum

class SchedulerClassConstError(Exception):
    """
        Error raised when the inputs to one of these clases fails to meet
            meet the guarantees (e.g. low_bound should be <= up_bound)
        
        Fields:
            message: explanation of the error.
    """
    def __init__(self, message):
        self.message=message


class SetConstraintType(Enum):
    """Enumerated constants for supported types of set constraints."""
    UNINITIALIZED = 0
    DEPARTMENT = 1
    SYNERGY = 2


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
        constraint_type: the constraint type represented as an integer. See SetConstraintType enum.
        low_bound: lower bound for the number of people from the set that should be in the office
                   on a given day if a department constraint. Mininum number of days that the entire set
                   should be in the office if a synergy constraint. Initialized to 0
        up_bound: upper bound for the number of people from the set that should be in the office on a
                   given day.  Initialized to -1, which is the stand in value for infinity.
                   Should only used for deparmtnet constraints, not for synergy constraints.
        personList: list of people in the set. Initialized to empty set.
        
    """
    
    def __init__(self, sid="", constraintType=SetConstraintType.UNINITIALIZED, personList=[], low_bound=0, up_bound=-1):
        self.sid = sid        
        if isinstance(constraintType, SetConstraintType):
            self.constraintType = constraintType
        else:
            raise SchedulerPrecondError("Invalid set constraint type. See SetConstraintType class for valid types.")
        
        if low_bound>=0 and (low_bound <= up_bound or up_bound == -1):
            self.low_bound=low_bound
            self.up_bound = up_bound
        else:
            raise SchedulerPrecondError("lower_bound and upper_bound do not make sense. They are either too small, too large, or upper_bound<lower_bound")
        
        self.personList=personList

