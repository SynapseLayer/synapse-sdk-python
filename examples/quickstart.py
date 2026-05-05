"""
Synapse Layer — Quickstart Example
Store a memory and recall it with semantic search.
Requires: pip install synapse-layer python-dotenv
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SYNAPSE_TOKEN", "")
USER_ID = os.getenv("SYNAPSE_USER_ID", "")
BASE_URL = os.getenv("SYNAPSE_BASE_URL", "https://forge.synapselayer.org")

if not TOKEN or TOKEN == "sk_connect_xxx":
    print("ERROR: Set SYNAPSE_TOKEN in .env (get yours at forge.synapselayer.org)")
    exit(1)


async def main():
    from synapse_layer import SynapseA2AClient

    async with SynapseA2AClient(api_key=TOKEN, base_url=BASE_URL) as client:
        # Store a memory
        print("[store] Saving memory...")
        await client.store_memory(
            user_id=USER_ID,
            content="The user prefers dark mode and communicates in Portuguese.",
            source_type="user_input",
            confidence=0.95,
        )
        print("[store] Done.\n")

        # Recall with semantic search
        print("[recall] Searching for user preferences...")
        result = await client.recall_memory(
            user_id=USER_ID,
            query="What are the user preferences?",
            limit=5,
        )

        if result and hasattr(result, "memories") and result.memories:
            for i, mem in enumerate(result.memories):
                print(f"  [{i}] content: {mem.content}")
                print(f"      tq_score: {getattr(mem, 'trust_quotient', 'N/A')}")
            print(f"\n[recall] {len(result.memories)} memories found.")
        else:
            print("[recall] No memories found (store may still be indexing).")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"ERROR: {e}")
        print("Check your SYNAPSE_TOKEN and network connectivity.")
