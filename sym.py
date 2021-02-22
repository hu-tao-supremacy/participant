#!/usr/bin/python3
import os

base = pathlib.Path(__file__).parent.absolute()

os.chdir(base)

def sym():
    os.chdir(base)
    src = "./hts"
    dst = "./apis/gen/python/hts"
    os.symlink(dst, src)

sym()
