#!/usr/bin/venv python
import unittest
import pytest
import pandas as pd
from embeddings import prepare_df

from extra.logger_config import setup_logger
logger = setup_logger(__name__)

@pytest.fixture
def raw_pdf_df():
    return pd.read_csv("data/rawdf.csv", index_col=0) 

def test_split_into_many_immutable(raw_pdf_df):
    raw_df = raw_pdf_df
    before_s = raw_df.text.str.cat(sep=' ')
    before_cnt = len(before_s.split(' '))
    for token_limit in [200,300,500]:
        after_s = prepare_df(raw_df, max_tokens=token_limit).text.str.cat(sep=' ')
        after_cnt = len(after_s.split(' ')) 
        assert before_cnt == after_cnt
    
if __name__ == '__main__':
    unittest.main()