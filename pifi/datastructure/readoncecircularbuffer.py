# A circular buffer with a fixed capacity.
#
# Appending is only possible if the buffer is not full.
#
# When you do `val = my_buffer[i]`, under the hood, the buffer will remove all values with index <= i.
# You can only access the items once; this makes room for more values.
class ReadOnceCircularBuffer():

    def __init__(self, capacity):
        # This represents the index of the first unread slot
        # remove items from start
        # None if the buffer is empty. Else, an integer in [0, __capacity)
        self.__start = None

        # number of items that have been added over this object's lifetime
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

        if self.__start is None:
            self.__start = len(self) % self.__capacity

        self.__len += 1

    # number of unread items in the buffer.
    # This should return an integer in the range: [0, __capacity]
    def unread_length(self):
        if self.__start is None:
            return 0
        first_empty_slot_idx = len(self) % self.__capacity
        if first_empty_slot_idx > self.__start:
            return first_empty_slot_idx - self.__start
        else:
            return self.__capacity - self.__start + first_empty_slot_idx

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

    # number of items that have been added over this object's lifetime
    def __len__(self):
        return self.__len

    def __repr__(self):
        return self.__data.__repr__() + ' (start: ' + str(self.__start) + ', len: ' + str(len(self)) + ')'
