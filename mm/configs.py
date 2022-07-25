import pandas as pd

class MmConfigs(dict):
    path = "/configs.json"
    def __init__(self):
        super().__init__()
        self.pd = pd.read_json('config.json')
        self.update(dict(self.pd))

