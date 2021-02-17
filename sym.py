#!/usr/bin/python3
import os

base = os.path.dirname(__file__)

os.chdir(base)

def sym():
    os.chdir(base)
    src = "./hts"
    dst = "./apis/gen/python/hts"
    os.symlink(dst, src)

sym()
