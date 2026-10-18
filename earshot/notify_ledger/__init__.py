"""
EARSHOT notify-ledger — MCP tool bindings.

The five tools, importable by the mcp-server lane directly:
    gate_notification, rescope_context, get_ledger, explain_withholding, undo_last
Plus factories for isolated state (tests, per-session servers):
    new_ledger, new_context_store, new_second_channel_queue
"""
from .ledger import Ledger, get_ledger, new_ledger
from .gating import (gate_notification, SecondChannelQueue,
                     new_second_channel_queue)
from .context import ContextStore, rescope_context
from .explain import explain_withholding
from .undo import undo_last

# Fresh per-server instances (avoids sharing module-global singletons across
# test servers). mcp-server should prefer these over the module defaults.
def new_context_store():
    return ContextStore()

__all__ = [
    "gate_notification",
    "rescope_context",
    "get_ledger",
    "explain_withholding",
    "undo_last",
    "Ledger",
    "ContextStore",
    "SecondChannelQueue",
    "new_ledger",
    "new_context_store",
    "new_second_channel_queue",
]
