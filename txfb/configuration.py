import json

config = None

def get_configuration():
    global config
    if config is None:
        config = json.load(open('/etc/imbored.json'))
    return config
