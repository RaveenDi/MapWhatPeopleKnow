"""Runtime limits and published prices (Standard mode, verified 2026-10-30: https://dev.meta.ai/docs/pricing-rate-limits)."""
import os

PROMPT_VERSION = 'evidence-resolver-v1'
# USD per million tokens. The cached-input discount is not modelled, so cost is a slight over-estimate.
PRICES = {'muse-spark-1.3': {'input': 1.25, 'output': 4.25}}
# Voice Transcribe is billed per audio hour; the response carries audioDurationMs and no token usage.
AUDIO_PRICES_PER_HOUR = {'muse-voice-transcribe-1.0': 0.18}
PRICING_STATUS = 'published Standard rates, verified 2026-10-30'

def max_calls():
    return max(0, int(os.getenv('MODEL_MAX_CALLS', '24')))

def max_completion_tokens():
    """Output cap for every chat request; reasoning tokens count against it (Muse Spark always reasons)."""
    return max(64, int(os.getenv('META_MAX_COMPLETION_TOKENS', '2048')))

def reasoning_effort():
    """META_REASONING_EFFORT = minimal|low|medium|high|xhigh (unset = API default). Lower is cheaper and faster."""
    value = os.getenv('META_REASONING_EFFORT', '').strip().lower()
    if value and value not in ('minimal', 'low', 'medium', 'high', 'xhigh'):
        raise ValueError('META_REASONING_EFFORT must be minimal, low, medium, high or xhigh')
    return value or None
