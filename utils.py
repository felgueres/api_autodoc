import json

def fill_html(path, **kwargs):
    import jinja2
    with open(path, 'r') as f:
        html = f.read()
    template = jinja2.Template(html)
    return template.render(**kwargs)

def generate_uuid(length=16):
    import secrets
    return secrets.token_hex(length)

def is_empty_string(s):
    return s is None or s == ''

from typing import List

def get_few_shot_example_messages(mode: str = "facts") -> List[dict]:
    with open("data/few_shot_examples.json", "r") as f:
        few_shot_examples = json.load(f)
    examples = few_shot_examples.get(mode, [])
    messages = []
    for e in examples:
        messages.append({
            "role": "user",
            "content": e["user"],
        })
        messages.append({
            "role": "assistant",
            "content": e["assistant"],
        })
    return messages

def validate_format(content):
    '''validates llm output is a json
    '''
    try:
        d = json.loads(content)
        if not isinstance(d, dict): return False
        # if not d.get('facts', None): return False
        # if not d.get('summary', None): return False
        return True
    except Exception as e:
        return False

def flatten_json(d, parent_key='', sep='_'):
    '''flattens a json object
    input_1 = { "a": [{"b1": 'a'}, {"b2": 'b'}, {"b3": 'c'}], "d": 4, "e": "hello" }
    expected_1 = { "a_b1": 'a', "a_b2": 'b', "a_b3": 'c', "d": 4, "e": "hello"}
    '''
    from collections.abc import MutableMapping
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_json(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, MutableMapping):
                    items.extend(flatten_json(item, new_key, sep=sep).items())
                else:
                    items.append((new_key + sep + str(i), item))
        else:
            items.append((new_key, v))
    return dict(items)

def get_few_shot_loop_json(section='facts', out_format='string'):
    '''returns the few shot loop json file as a dict
    '''
    with open("data/few_shot_loop.json", "r") as f:
        if out_format == 'dict':
            return json.load(f)[section]
        elif out_format == 'string':
            return json.dumps(json.load(f)[section], indent=4)
        else:
            raise ValueError(f'out_format must be string or dict, got {out_format}')