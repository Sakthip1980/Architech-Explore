"""
simulator.hardware — Self-consistent hardware block system

Public API
----------
parse_unit(raw)        -> (float, unit_str)
PropertyNode           - single property slot
PropertySchema         - collection of properties with physics solver
Block                  - base hardware block (Module + PropertySchema)
ComputeBlock           - compute unit (CPU/GPU/NPU/systolic array)
MemoryBlock            - memory module (DRAM/HBM/cache/scratchpad)
InterconnectBlock      - link or bus (AXI/PCIe/CXL/NoC)
PowerDomain            - shared voltage / leakage source
ClockDomain            - shared clock frequency source
block_from_module()    - wrap existing Module subclass as a Block
TransactionState       - enum: CREATED→QUEUED→GRANTED→IN_FLIGHT→RECEIVED→COMPLETED
Transaction            - one data transfer with cycle timestamps
Connection             - unidirectional link with queue and energy tracking
BlockRegistry          - name→Block lookup table
"""

from .properties import parse_unit, PropertyNode, PropertySchema, ConflictWarning
from .blocks import (
    Block,
    ComputeBlock,
    MemoryBlock,
    InterconnectBlock,
    PowerDomain,
    ClockDomain,
    block_from_module,
)
from .connections import TransactionState, Transaction, Connection, make_transaction
from .registry import BlockRegistry

__all__ = [
    # properties
    'parse_unit',
    'PropertyNode',
    'PropertySchema',
    'ConflictWarning',
    # blocks
    'Block',
    'ComputeBlock',
    'MemoryBlock',
    'InterconnectBlock',
    'PowerDomain',
    'ClockDomain',
    'block_from_module',
    # connections
    'TransactionState',
    'Transaction',
    'Connection',
    'make_transaction',
    # registry
    'BlockRegistry',
]
