# A circular buffer with a fixed capacity.
#
# Appending is only possible if the buffer is not full.
#
# When you do `val = my_buffer[i]`, under the hood, the buffer will remove all values with index <= i.
# You can only access the items once; this makes room for more values.
class AppendOnlyCircularBuffer():

    # remove items from start
    __start = None

    # number of items that have been added over this object's lifetime
    __len = 0

    __max_gotten_index = -1

    __capacity = None
    __data = []

    def __init__(self, capacity):
        self.__start = None
        self.__len = 0
        self.__max_gotten_index = -1
        self.__capacity = capacity
        self.__data = []

    def is_full(self):
        return self.__start == (len(self) % self.__capacity)

    def append(self, value):
        if self.is_full():
            raise Exception('buffer is full!')

        if len(self.__data) >= self.__capacity:
            self.__data[len(self) % self.__capacity] = value
        else:
            self.__data.append(value)

        if self.__start == None:
            self.__start = len(self) % self.__capacity

        self.__len += 1

    def __getitem__(self, index):
        if index >= len(self) or index < 0:
            raise IndexError('index out of range')

        if index <= self.__max_gotten_index:
            raise IndexError('index already gotten')

        item = self.__data[index % self.__capacity]
        self.__start = (index + 1) % self.__capacity
        if self.is_full():
            # We wrapped around and actually the buffer is empty
            self.__start = None

        if index > self.__max_gotten_index:
            self.__max_gotten_index = index
        return item

    def __len__(self):
        return self.__len

    def __repr__(self):
        return self.__data.__repr__() + ' (start: ' + str(self.__start) + ', len: ' + str(len(self)) + ')'
