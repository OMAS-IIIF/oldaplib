import json
from enum import Enum

from oldaplib.src.helpers.serializer import serializer



if __name__ == '__main__':
    def gaga(*, var1, var2, spec1, spec2, **kwargs):
        print(var1, var2, spec1, spec2)
        for key, value in kwargs.items():
            print(key, value)

    spec = {'spec1': 'SPEZ1', 'spec2': 'SPEZ2'}
    gaga(var1='A', var2='B', **spec, var3='E', var4='F')