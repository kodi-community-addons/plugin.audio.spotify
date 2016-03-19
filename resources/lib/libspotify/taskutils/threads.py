'''
Created on 22/10/2011

@author: mikel
'''
import collections
import threading
from compat import AtomicEvent
import traceback
import time



#Thread local var storage
__thread_locals = threading.local()


def current_task():
    return __thread_locals.current_task


def set_current_task(task):
    __thread_locals.current_task = task


def remove_current_task():
    del __thread_locals.current_task



class TaskError(Exception):
    pass



class TaskCancelledError(TaskError):
    pass



class TaskWaitTimedOutError(TaskError):
    pass



class TaskCreateError(TaskError):
    pass



class TaskItem:
    __target = None
    __group = None
    __args = None
    __kwargs = None
    
    __wait_event = None
    __end_event = None
    
    __is_running = None
    __is_cancelled = None
    
    
    def __init__(self, target, group=None, *args, **kwargs):
        self.__target = target
        self.__group = group
        self.__args = args
        self.__kwargs = kwargs
        self.__wait_event = AtomicEvent()
        self.__end_event = AtomicEvent()
        self.__is_running = False
        self.__is_cancelled = False
    
    
    def _generate_group(self):
        if hasattr(self.__target, 'im_class'):
            path = [
                self.__target.im_class.__module__,
                self.__target.im_class.__name__,
                self.__target.__name__
            ]
            
        else:
            path = [
                self.__target.__module__,
                self.__target.__name__
            ]
        
        return '.'.join(path)
    
    
    def check_status(self):
        if self.__is_cancelled:    
            #TODO: Report task id in exception message
            raise TaskCancelledError("Task cancelled")
    
    
    def try_wait(self, timeout=None):
        status = self.__wait_event.wait(timeout)
        self.__wait_event.clear()
        
        #Check if it was cancelled
        self.check_status()
        
        #Return event status on exit
        return status
    
    
    def wait(self, timeout=None):
        status = self.try_wait(timeout)
        
        #Raise an exception if a timeout is detected
        if not status:
            raise TaskWaitTimedOutError("Task timed out")
    
    
    def _eval_condition(self, condition):
        
        #Check if it's callable
        if hasattr(condition, '__call__'):
            return condition()
        
        #Evaluate it directly
        else:
            return condition
    
    
    def condition_wait(self, condition, timeout=None):
        start_time = time.time()
        
        while True:
            
            #Check for condition status
            if self._eval_condition(condition):
                return
            
            #Perform the actual wait
            if timeout is None:
                self.wait()
            else:
                consumed_time = time.time() - start_time
                self.wait(timeout - consumed_time)
    
    
    def notify(self):
        self.__wait_event.set()
    
    
    def cancel(self):
        self.__is_cancelled = True
        self.notify()
    
    
    def is_cancelled(self):
        return self.__is_cancelled
    
    
    def get_group(self):
        if self.__group is None:
            self.__group = self._generate_group()
        
        return self.__group
    
    
    def run(self):
        try:
            set_current_task(self)
            self.__is_running = True
            self.__target(*self.__args, **self.__kwargs)
        
        
        except TaskCancelledError:
            print "Task was cancelled"
        
        except Exception as ex:
            print "Unhandled exception in task:"
            traceback.print_exc()
        
        finally:
            self.__is_running = False
            self.__end_event.set()
            remove_current_task()
        
    
    def is_running(self):
        return self.__is_running
        
    
    def join(self, timeout=None):
        return self.__end_event.wait(timeout)



class TaskQueueManager:
    __groups = None
    __mutex = None
    
    
    def __init__(self):
        self.__groups = {}
        self.__mutex = threading.Lock()
    
    
    def has_group(self, group):
        return group in self.__groups
    
    
    def get_tasks(self, group):
        self.__mutex.acquire()
        
        try:
            #Avoid returning the live queue
            result = list(self.__groups[group])
        
        finally:
            self.__mutex.release()
        
        return result
    
    
    def add(self, task):
        self.__mutex.acquire()
        
        try:
            group = task.get_group()
            
            #New container queue needed
            if not self.has_group(group):
                self.__groups[group] = collections.deque([task])
            
            #Append task to existing queue normally
            else:
                self.__groups[group].append(task)
        
        finally:
            self.__mutex.release()
    
    
    def _remove(self, container, task):
        #Queue has remove()!
        if hasattr(container, 'remove'):
            container.remove(task)
        
        #pre-2.5, no remove(), snif.
        else:
            for idx, item in enumerate(container):
                if item == task:
                    del container[idx]
                    return
    
    
    def remove(self, task):
        self.__mutex.acquire()
        
        try:
            group = task.get_group()
            
            if group not in self.__groups:
                raise KeyError('Unknown group id: %s' % group)
            
            #Remove the task first
            self._remove(self.__groups[group], task)
            
            #If queue queue reached to zero length, remove it
            if len(self.__groups[group]) == 0:
                del self.__groups[group]
        
        finally:
            self.__mutex.release()
    
    
    def clear_group(self, group):
        self.__mutex.acquire()
        
        try:
            if group not in self.__groups:
                raise KeyError('Unknown group id: %s' % group)
            
            del self.__groups[group]
        
        finally:
            self.__mutex.release()
    
    
    def clear(self):
        self.__mutex.acquire()
        
        try:
            self.__groups = {}
            
        finally:
            self.__mutex.release()



class TaskCountManager:
    __groups = None
    __tasks = None
    __mutex = None
    
    
    def __init__(self):
        self.__groups = {}
        self.__tasks = []
        self.__mutex = threading.Lock()
    
    
    def can_run(self, task, max_concurrency):
        self.__mutex.acquire()
        
        try:
            if max_concurrency == 0:
                result = True
            
            elif task.get_group() not in self.__groups:
                result = True
            
            elif len(self.__groups[task.get_group()]) < max_concurrency:
                result = True
            
            else:
                result = False
        
        finally:
            self.__mutex.release()
        
        return result
    
    
    def add_task(self, task):
        self.__mutex.acquire()
        
        try:
            #Add the task to the general queue first
            self.__tasks.append(task)
            
            if task.get_group() not in self.__groups:
                self.__groups[task.get_group()] = [task]
            
            else:
                self.__groups[task.get_group()].append(task)
        
        finally:
            self.__mutex.release()
    
    
    def get_tasks(self, group=None):
        self.__mutex.acquire()
        
        try:
            if group is None:
                result = list(self.__tasks)
            else:
                result = list(self.__groups[group])
        
        finally:
            self.__mutex.release()
        
        return result
    
    
    def remove_task(self, task):
        self.__mutex.acquire()
        
        try:
            #Remove from general task list
            self.__tasks.remove(task)
            
            if task.get_group() not in self.__groups:
                raise KeyError('Unknown group id: %s' % task.get_group())
            
            elif len(self.__groups[task.get_group()]) == 1:
                del self.__groups[task.get_group()]
            
            else:
                self.__groups[task.get_group()].remove(task)
        finally:
            self.__mutex.release()



class TaskManager:
    #Static class instances
    __queue_manager = TaskQueueManager()
    __count_manager = TaskCountManager()
    __add_mutex = threading.Lock()
    __continue_sem = threading.Semaphore()
    
    
    def _get_next_task(self, group, max_concurrency):
        for task in self.__queue_manager.get_tasks(group):
            if self.__count_manager.can_run(task, max_concurrency):
                return task
        
        return None
    
    
    def _task_post(self, task, max_concurrency):
        
        self.__continue_sem.acquire()
        
        try:
            
            #Decrement task count
            self.__count_manager.remove_task(task)
            
            #A shortcut to the task's group
            group = task.get_group()
            
            #Handle enqueued tasks
            if self.__queue_manager.has_group(group):
                
                #Get the next runnable task on the container
                next_task = self._get_next_task(group, max_concurrency)
                
                #If it got started remove it from the queue
                if next_task is not None:
                    
                    if self._try_start(next_task, max_concurrency):
                        self.__queue_manager.remove(next_task)
        finally:
            self.__continue_sem.release()
    
    
    def _try_start(self, task, max_concurrency):
        def runner():
            #Run the actual task
            task.run()
            
            #And execute post actions
            self._task_post(task, max_concurrency)
        
        #Try running the task
        if self.__count_manager.can_run(task, max_concurrency):
            
            #Register that task
            self.__count_manager.add_task(task)
            
            #And start it in a thread
            thread = threading.Thread(target=runner)
            thread.start()
            
            return True
        
        else:
            return False
    
    
    def cancel_all(self):
        
        self.__continue_sem.acquire()
        
        try:
            
            #Cancel every running task
            for item in self.__count_manager.get_tasks():
                item.cancel()
                item.join()
            
            #Now cancel all the tasks queued in the meantime
            self.__queue_manager.clear()
            
        finally:
            self.__continue_sem.release()
    
    
    def add(self, target, group=None, max_concurrency=0, *args, **kwargs):
        task = TaskItem(target, group, *args, **kwargs)
        
        self.__add_mutex.acquire()
        
        try:
            #Enqueue if we can't start it
            if not self._try_start(task, max_concurrency):
                self.__queue_manager.add(task)
        
        finally:
            self.__add_mutex.release()
        
        return task
