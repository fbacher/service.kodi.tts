# coding=utf-8

DEVELOPMENT = True
try:
    from typing import (Any, Callable, FrozenSet, Optional, Iterable, List, Dict, Set,
                        Tuple,
                        Sequence, Union)

    TextType = str
    MovieType = Dict[TextType, Any]

except (Exception):
    DEVELOPMENT = False
    Any = None
    Callable = None
    FrozenSet = None
    Optional = None
    Iterable = None
    List = None
    Dict = None
    Tuple = None
    Sequence = None
    Set = None
    Union = None
    TextType = str
    MovieType = None

RESOURCE_LIB = True
try:
    import resource
except (ImportError):
    resource = None
    RESOURCE_LIB = False
