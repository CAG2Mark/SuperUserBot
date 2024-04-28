def datawrite(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.export()
        return result
    return wrapper

def mutex(*args_, **kwargs_):
    def w1(func):
        def wrapper(self, *args, **kwargs):
            with kwargs_["lock"]:
                val = func(self, *args, **kwargs)
            return val
        return wrapper
    return w1