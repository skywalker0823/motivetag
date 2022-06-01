
import re

def filter(data):
    box = []
    keys = re.findall("#\S+", data)
    for key in keys:
        key = key.split("#")[1]
        box.append(key)
    return box