from collections import OrderedDict

class LimitedSizeDict(OrderedDict):

    __capacity = None

    def __init__(self, items = [], capacity = 10):
        self.__capacity = capacity
        super().__init__(items[-self.__capacity:])

    def __setitem__(self, key, value):
        if len(self) >= self.__capacity and key not in self:
            self.popitem(last = False)
        super().__setitem__(key, value)
