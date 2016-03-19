'''
Created on 07/05/2013

@author: mikel
'''
class ConditionList:
    __conditions = None
    
    def __init__(self):
        self.__conditions = []
    
    
    def add_condition(self, condition):
        self.__conditions.append(condition)
    
    
    def check_conditions(self):
        #Generate a new list with false conditions
        self.__conditions = [item for item in self.__conditions if not item()]
            
        #If list size reaches to zero all conditions have been met
        if len(self.__conditions) == 0:
            return True
        
        else:
            return False
    
    
    def __nonzero__(self):
        return self.check_conditions()
    
    
    def __bool__(self):
        return self.check_conditions()
