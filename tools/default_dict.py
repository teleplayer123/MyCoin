class defaultdict(dict):
    def __init__(self, default=None, *args, **kwargs):
        if (default is not None and
            not hasattr(default, "__call__")):
            raise TypeError("default must be callable")
        dict.__init__(self, *args, **kwargs)
        self.default = default
    
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default is None:
            raise KeyError(key)
        self[key] = value = self.default()
        return value