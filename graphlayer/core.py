from . import iterables


def define_graph(expanders):
    return GraphDefinition(expanders)

    
class GraphDefinition(object):
    def __init__(self, expanders):
        self._expanders = iterables.to_dict(
            (expander.type, expander)
            for expander in _flatten(expanders)
        )
    
    def create_graph(self, dependencies=None):
        if dependencies is None:
            dependencies = {}

        return Graph(self._expanders, dependencies)


class Graph(object):
    def __init__(self, expanders, dependencies):
        self._expanders = expanders
        self._dependencies = dependencies
    
    def expand(self, *args, **kwargs):
        type = kwargs.pop("type", None)
        if type is None:
            type = args[0].type
        # TODO: better error
        assert not kwargs
        expander = self._expanders[type]
        dependencies = getattr(expander, "dependencies", dict())
        kwargs = iterables.to_dict(
            (arg_name, self._dependencies[dependency_key])
            for arg_name, dependency_key in dependencies.items()
        )
        return expander(self, *args, **kwargs)


def _flatten(value):
    if isinstance(value, list):
        return [
            subelement
            for element in value
            for subelement in _flatten(element)
        ]
    elif hasattr(value, "expanders"):
        return _flatten(value.expanders)
    else:
        return [value]


def expander(type):
    def register_expander(func):
        func.type = type
        return func
    
    return register_expander


def dependencies(**kwargs):
    def register_dependency(func):
        func.dependencies = kwargs
        return func
    
    return register_dependency
