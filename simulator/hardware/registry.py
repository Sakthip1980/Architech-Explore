"""
Global block registry — maps block names to Block instances.

Allows the rest of the simulator to look up blocks by name without
passing references everywhere.
"""

from typing import Dict, Optional, List
from .blocks import Block


class BlockRegistry:
    """
    Singleton-style registry for named Block instances.

    Usage
    -----
    registry = BlockRegistry()
    registry.register(my_block)
    blk = registry.get('my_npu')
    all_compute = registry.filter(block_type='ComputeBlock')
    """

    def __init__(self):
        self._blocks: Dict[str, Block] = {}

    def register(self, block: Block, name: Optional[str] = None) -> 'BlockRegistry':
        """Register a block. Uses block.name unless overridden."""
        key = name or block.name
        if key in self._blocks:
            raise ValueError(f"Block {key!r} is already registered. "
                             f"Use a unique name or call unregister() first.")
        self._blocks[key] = block
        return self

    def unregister(self, name: str) -> Optional[Block]:
        """Remove and return a block by name, or None if not found."""
        return self._blocks.pop(name, None)

    def get(self, name: str) -> Optional[Block]:
        """Return the Block registered under name, or None."""
        return self._blocks.get(name)

    def get_or_raise(self, name: str) -> Block:
        """Return the Block or raise KeyError."""
        if name not in self._blocks:
            raise KeyError(f"No block registered with name {name!r}. "
                           f"Available: {sorted(self._blocks)}")
        return self._blocks[name]

    def filter(self, block_type: Optional[str] = None) -> List[Block]:
        """
        Return blocks optionally filtered by class name.

        block_type: exact class name string, e.g. 'ComputeBlock', 'MemoryBlock'
        """
        if block_type is None:
            return list(self._blocks.values())
        return [b for b in self._blocks.values()
                if b.__class__.__name__ == block_type]

    def all_names(self) -> List[str]:
        """Return sorted list of all registered block names."""
        return sorted(self._blocks.keys())

    def clear(self) -> None:
        """Remove all registered blocks."""
        self._blocks.clear()

    def __len__(self) -> int:
        return len(self._blocks)

    def __contains__(self, name: str) -> bool:
        return name in self._blocks

    def __repr__(self):
        names = self.all_names()
        return f"BlockRegistry({len(names)} blocks: {names})"
