# Inputs: PDF file
# Outputs: JSON with key value pairs

####
# Approach A. Rolling window with starting map of key value pairs, where key is the feature is known and value is in the RFQ 
# 1. rolling window of 1000 tokens of content
# 2. if value is not present, then fill JSON with blank
# 3. if value is present, then fill JSON with value 
# 4. Repeat until end of document
# 5. Consolidate JSONs into one, where you provide a list of choices for each key value pair
# 6. Show in the UI 
# 7. User selects the correct value
# 8. User can also edit the value 
# 9. User can export the JSON in CSV format

#### 
# Approach B. Single call to extract all key value pairs using a more powerful model  

# Approach C. One call per question where the question is the key and the answer is the value
####

# This file implements A

class MissingEmbeddingsError(Exception):
    pass

def consolidate_choices(choices):
    d_out = {}
    for d in choices:
        for k, v in d.items():
            k = k.lower()   
            if k not in d_out:
                d_out[k] = []
            d_out[k].append(v)
    return d_out
