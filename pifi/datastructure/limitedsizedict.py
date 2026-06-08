from collections import OrderedDict
from typing import Any

class LimitedSizeDict(OrderedDict[Any, Any]):

    def __init__(self, items = None, capacity = 10):
        self.__capacity = capacity
        if items is None:
            items = []
        super().__init__(items[-self.__capacity:])

    def __setitem__(self, key, value):
        if len(self) >= self.__capacity and key not in self:
            self.popitem(last = False)
        super().__setitem__(key, value)
