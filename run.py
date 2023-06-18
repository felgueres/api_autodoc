# Framework to evaluate LLM outputs for data extraction tasks

import argparse
import os
from prompts import compare_prompt, standard_prompt
from gpt import gpt
import re
from functools import partial
import json

DATA_PATH = './data'

class Task:
    def __init__(self):
        pass
    def __len__(self) -> int:
        pass
    def get_input(self, idx:int) -> str:
        pass
    def test_output(self, idx:int, output:str) -> bool:
        pass

class ExtractTask(Task):
    '''
    Inputs: 
        (a) : a text from a document 
        (b) : a key phrase used to extract
    Output: 
        (y) : a key-value pair extracted from (a) where the key is (b) 
    Input Example:
        (a) : "The quick brown fox jumps over lazy dog"
        (b) : "fox_color"
    Output Example:
        (y) : {{'fox_color': 'brown'}} 
    '''
    def __init__(self, file='data/evals_extract.jsonl'):
        super().__init__()
        path = os.path.join(DATA_PATH, file)
        self.data = open(path, 'r').readlines()
        self.stops = ['\nPassages:\n', None]
    
    def get_input(self, idx: int) -> str:
        return json.loads(self.data[idx])['input']
    
    def get_label(self, idx:int) -> str:
        return json.loads(self.data[idx])['output']
    
    def test_output(self, idx: int, output: str, expected:str): 
        prompt = self.compare_prompt_wrap(y_pred=output, y_exp=expected)
        score_outputs = gpt(prompt, n=1, model='gpt-3.5-turbo')
        scores = []
        for score_output in score_outputs:
            pattern = r".*similarity score is (\d+).*" 
            match = re.match(pattern, score_output, re.DOTALL)
            if match:
                score = int(match.groups()[0])
                scores.append(score)
            else:
                print(f'--------------------score no match: {[score_output]}')
        info = {'rs': scores, 'r': sum(scores) / len(scores) if scores else 0}
        return info
    
    @staticmethod
    def standard_prompt_wrap(x:dict, y:str='') -> str:
        return standard_prompt.format(passages=x['text'], key=x['key']) + y
    
    @staticmethod
    def compare_prompt_wrap(y_pred: str, y_exp: str) -> str:
        prompt = compare_prompt + f'Dictionary 1:\n{y_pred}\n\nDictionary 2:\n{y_exp}\n'
        return prompt

    
def get_task(name, file=None):
    if name == 'extract':
        return ExtractTask(file)
    else:
        raise NotImplementedError

# NOTE: variable y is useful only when using cot or tot, not naive solve
def get_samples(task, x, y, n_generate_sample, stop):
    prompt = task.standard_prompt_wrap(x,y)
    samples = gpt(prompt, n=n_generate_sample, stop=stop)
    return [y + _ for _ in samples]

def solve(args, task, idx):
    x = task.get_input(idx)
    ys = get_samples(task, x, '', args.n_generate_sample, stop=None)
    return ys, {}

def run(args):
    task = get_task(args.task, args.task_file_path)
    logs,cnt_avg,cnt_any = [],0,0
    global gpt 
    gpt = partial(gpt, model=args.model, temperature=args.temperature)
    file = f'logs/{args.task}/{args.model}_{args.method_retrieve}.json'
    os.makedirs(os.path.dirname(file), exist_ok=True)

    for i in range(args.task_start_idx, args.task_end_idx):
        ys,info = solve(args, task, i)
        y_label = task.get_label(i)
        infos = [task.test_output(i,y,y_label) for y in ys]
        info.update({'idx': i, 'ys': ys, 'infos': infos})
        logs.append(info)
        with open(file, 'w') as f:
            json.dump(logs, f, indent=4)

        accs = [info['r'] for info in infos]
        cnt_avg += sum(accs) / len(accs)
        cnt_any += any(accs)
        # print(i, 'sum(accs)', sum(accs), 'cnt_avg', cnt_avg, 'cnt_any', cnt_any, '\n')
    
    n = args.task_end_idx - args.task_start_idx
    print(cnt_avg / n, cnt_any / n)
    print(f'Finished running {n} tasks.')


def parse_args():
    args = argparse.ArgumentParser()
    args.add_argument('--model', type=str, choices=['gpt-3.5-turbo', 'gpt-4'], default='gpt-3.5-turbo')
    args.add_argument('--temperature', type=float, default=0.5)
    args.add_argument('--task', type=str, choices=['extract'])
    args.add_argument('--task_file_path', type=str, required=True)
    args.add_argument('--task_start_idx', type=int, default=0)
    args.add_argument('--task_end_idx', type=int, default=1)
    args.add_argument('--method_retrieve', type=str, choices=['top_k']) 
    args.add_argument('--method_generate', type=str, choices=['sample'])
    # Add method_evaluate to support evaluation-based prompting techinques, eg. voting, scoring 
    args.add_argument('--n_generate_sample', type=int, default=1)
    args = args.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    run(args)