# load json file from data called few_shot_loop.json

import json

with open('data/few_shot_loop.json') as f:
    data = json.load(f)

# print with indentation

print(json.dumps(data, indent=4)) 
