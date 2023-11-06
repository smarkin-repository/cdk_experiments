import pytest
import json
import os


@pytest.fixture
def snapshot():
    # read json file from 'data' director
    with open(os.path.join(os.path.dirname(__file__), 'data', 'WorkShopEC2Spot.template.json')) as f:
        data = json.load(f) 
    return data