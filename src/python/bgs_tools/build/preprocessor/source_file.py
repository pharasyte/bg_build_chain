
class SourceFile:
    def __init__(self, path):
        self.path = path
        self.lines = []
        self.includes = []
        self.defines = []
        self.undefines = []
        self.ifdefs = []
        self.ifdefs = []
        self.ifdefs_stack = []