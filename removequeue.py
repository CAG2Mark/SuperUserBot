from threading import Lock
from utils import mutex, datawrite

import heapq

import os

import json

FILE="removequeue.json"

lock = Lock()
filelock = Lock()

# use a min-heap to get the next removal time
class RemoveQueue:
    def __init__(self):
        self.queue = []

    @mutex(lock=lock)
    @datawrite
    def add(self, del_time: int, user: int, guild: int, role: int):
        heapq.heappush(self.queue, (del_time, user, guild, role))

    @mutex(lock=lock)
    def get_min_time(self):
        if self.queue:
            return self.queue[0][0]
        return -1
    
    @mutex(lock=lock)
    @datawrite
    def pop(self):
        if self.queue:
            return heapq.heappop(self.queue)
        return None
    
    @mutex(lock=filelock)
    def export(self):
        with open(FILE, 'w') as f:
            json.dump(self.queue, f)
    
    @mutex(lock=filelock)
    def load(self):
        if not os.path.exists(FILE): 
            return

        with open(FILE, 'r') as f:
            self.queue = json.load(f)
        
        heapq.heapify(self.queue)
