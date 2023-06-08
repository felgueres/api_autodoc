import sys 
sys.path.append('../')
import json
from utils import flatten_json, validate_format

def test_flatten_json():
    input_1 = { "a": [{"b1": 'a'}, {"b2": 'b'}, {"b3": 'c'}], "d": 4, "e": "hello" }
    expected_1 = { "a_b1": 'a', "a_b2": 'b', "a_b3": 'c', "d": 4, "e": "hello"}
    input_2 = { "a": [{"b1": 'a'}, {"b2": 'b'}, {"b3": 'c'}], "d": 4, "e": "hello", "f": {'g': 'h'} }
    expected_2 = { "a_b1": 'a', "a_b2": 'b', "a_b3": 'c', "d": 4, "e": "hello", "f_g": 'h'}
    input_3 = { 'a': ['a', 'b', 'c'], 'b': {'c': 'd', 'e': 'f'}, }
    expected_3 = { 'a_0': 'a', 'a_1': 'b', 'a_2': 'c', 'b_c': 'd', 'b_e': 'f', }
    input_4 = {'a': [{'b': { 'c': 'd' }}, {'d': 'e'}]}
    expected_4 = { 'a_b_c': 'd', 'a_d': 'e'}
    input_5 = { 'a': { 'b': ['a','b', { 'c': 'd', }] } } 
    expected_5 = { 'a_b_0': 'a', 'a_b_1': 'b', 'a_b_c': 'd'}
    assert flatten_json(input_1) == expected_1 
    assert flatten_json(input_2) == expected_2
    assert flatten_json(input_3) == expected_3
    assert flatten_json(input_4) == expected_4
    assert flatten_json(input_5) == expected_5

def test_validate_format():
    input_1 = "{\n \"facts\": [\n {\"b1\": \"a\"},\n {\"b2\": \"b\"},\n {\"b3\": \"c\"}\n ],\n \"summary\": \"hello\"\n}"
    input_2 = "{\n \"facts\": \"\"\n}"
    input_3 = "{\n \"summary\": \"\"\n}"
    input_4 = "{\n \"facts\": \"\"\n}, {\n \"summary\": \"\"\n}"
    input_5 = json.dumps({"facts": 
    {"trend_1_description": "Building replicable workflows with self-service capabilities, or engineering platforms, is a key theme at tech companies in the last 10 years", 
     "applications_undergoing_platformization_process": ["Machine learning", "Experimentation", "Analytics", "Deployment"]}, 
    "summary": "The future of software development lies in replicable and reliable workflows that provide user experiences. Configuration will play a crucial role in this process as code becomes easier to generate and scale. Two major trends shaping this future are the platformization of various applications and the use of large language models like OpenAI's Codex to write code with high accuracy."})
    assert validate_format(input_1) == True 
    assert validate_format(input_2) == False
    assert validate_format(input_3) == False
    assert validate_format(input_4) == False
    assert validate_format(input_5) == True 
