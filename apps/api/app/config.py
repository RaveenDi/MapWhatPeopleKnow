"""Runtime limits and illustrative prices, NOT verified Meta pricing."""
import os

PROMPT_VERSION = 'evidence-resolver-v1'
# USD per million tokens; placeholders only. Audio pricing is unknown.
PRICES_UNVERIFIED = {'muse-spark-1.3': {'input': 1.0, 'output': 1.0}}

def max_calls():
    return max(0, int(os.getenv('MODEL_MAX_CALLS', '24')))
