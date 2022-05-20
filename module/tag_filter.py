
import re

def filter(data):
    box = []
    keys = re.findall("#\S+", data)
    print(keys)
    for key in keys:
        key = key.split("#")[1]
        box.append(key)
    print(box)
    return box