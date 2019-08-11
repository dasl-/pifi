# An append only circular buffer
#
# Values may be read via array indexing.
# Supports getting items from index [0, capacity).
# Oldest element at index 0.
# Newest element at index capacity - 1.
class AppendOnlyCircularBuffer():

    # add items at the start
    __start = None

    __capacity = None
    __data = []

    def __init__(self, capacity):
        self.__start = None
        self.__capacity = capacity
        self.__data = []

    def is_full(self):
        return len(self) == self.__capacity

    def append(self, value):
        if self.is_full():
            self.__data[self.__start] = value
            self.__start = (self.__start + 1) % self.__capacity
        else:
            self.__data.append(value)
            if self.__start == None:
                self.__start = 0

    # supports getting items from index [0, __capacity).
    # Oldest element at index 0.
    # Newest element at index __capacity - 1.
    def __getitem__(self, index):
        if index >= len(self) or index < 0:
            raise IndexError('index out of range')

        remapped_index = (self.__start + index) % self.__capacity
        return self.__data[remapped_index]

    def __len__(self):
        return len(self.__data)

    def __repr__(self):
        return self.__data.__repr__() + ' (start: ' + str(self.__start) + ', len: ' + str(len(self)) + ')'
