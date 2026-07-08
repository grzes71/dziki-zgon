class Command:
    def undo(self):
        pass

    def redo(self):
        pass

class HistoryManager:
    def __init__(self, max_depth=100):
        self.max_depth = max_depth
        self.undo_stack = []
        self.redo_stack = []

    def execute(self, command: Command):
        command.redo()
        self.undo_stack.append(command)
        if len(self.undo_stack) > self.max_depth:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            command = self.undo_stack.pop()
            command.undo()
            self.redo_stack.append(command)

    def redo(self):
        if self.redo_stack:
            command = self.redo_stack.pop()
            command.redo()
            self.undo_stack.append(command)

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
