# test_aml_client.py
from .aml_client import aml_predict

features = [0.0] * 165
features[0] = 1000.0

print(aml_predict(features))
