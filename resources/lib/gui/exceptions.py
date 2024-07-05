# coding=utf-8


class ParseError(Exception):

    def __init__(self, msg: str = ''):
        super().__init__(msg)
