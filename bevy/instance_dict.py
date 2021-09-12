from collections import UserDict


class InstanceDict(UserDict):
    def __contains__(self, item):
        return super().__contains__(_KeyWrapper(item))

    def __delitem__(self, item):
        return super().__delitem__(_KeyWrapper(item))

    def __getitem__(self, item):
        return super().__getitem__(_KeyWrapper(item))

    def __setitem__(self, key, value):
        super().__setitem__(_KeyWrapper(key), value)


class _KeyWrapper:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return id(other.value) == id(self.value)

    def __hash__(self):
        return id(self.value)
