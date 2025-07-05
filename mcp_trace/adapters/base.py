from abc import ABC, abstractmethod

class TraceAdapter(ABC):
    @abstractmethod
    def export(self, trace_data: dict):
        pass 