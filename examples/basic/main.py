#!/usr/bin/env python3
"""Synapse Layer — Basic Example

Usage:
    export SYNAPSE_TOKEN="sk_connect_YOUR_TOKEN"
    python main.py

Get your token at https://forge.synapselayer.org/dashboard/connect
"""

from synapse_layer import Synapse

# Initialize (reads SYNAPSE_TOKEN from env, or pass token= directly)
s = Synapse()

# Store a memory
s.save("user likes coffee")
print("\u2705 Memory saved")

# Recall it
results = s.recall("what does user like?")
print(f"\u2705 Found {len(results)} memories:")
for r in results:
    tq = r.get("trust_quotient", "?")
    content = r.get("content", str(r))
    print(f"  [TQ={tq}] {content}")
