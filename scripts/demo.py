#!/usr/bin/env python3
"""Synapse Layer — 30-Second Demo

Run:
    export SYNAPSE_TOKEN="sk_connect_YOUR_TOKEN"
    python scripts/demo.py

Get your token at https://forge.synapselayer.org/dashboard/connect
"""

from synapse_layer import Synapse

s = Synapse()  # reads SYNAPSE_TOKEN from env

# Save
result = s.save("user likes coffee")
print("--- SAVED ---")
print("user likes coffee")
print()

# Recall
memories = s.recall("what does user like?")
print("--- RECALL ---")
for m in memories:
    print(m.get("content", m))
