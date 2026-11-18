"""
pack_alias.py
One copy of the pack, whatever name it is imported under.

ComfyUI loads a custom node folder under a name made from its disk path. Older
nodes of this pack import it as "AAA_Metadata_System" or as
"custom_nodes.AAA_Metadata_System". Without help Python treats those as other
packages: the whole pack started a second time (every node module loaded twice),
and with the folder named differently - the Comfy registry installs it as
"aaa-metadata-system" - those imports found nothing at all.

install() makes both names, and every module below them, resolve to the modules
already loaded under the real name.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import importlib
import importlib.abc
import importlib.machinery
import sys
from typing import Optional

ALIASES = ("AAA_Metadata_System", "custom_nodes.AAA_Metadata_System")


class PackAliasFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, real_name: str):
        self.real_name = real_name

    def real(self, fullname: str) -> Optional[str]:
        for alias in ALIASES:
            if alias == self.real_name:
                continue
            if fullname == alias or fullname.startswith(alias + "."):
                return self.real_name + fullname[len(alias):]
        return None

    # finder
    def find_spec(self, fullname, path=None, target=None):
        if self.real(fullname) is None:
            return None
        return importlib.machinery.ModuleSpec(fullname, self)

    # loader: hand back the module that already exists under the real name
    def create_module(self, spec):
        return importlib.import_module(self.real(spec.name))

    def exec_module(self, module):
        return None


def install(real_name: str) -> bool:
    """Called first thing by the pack's __init__ with its own __name__.
    False when the pack is already loaded under another name (nothing is changed then)."""
    module = sys.modules.get(real_name)
    if module is None:
        return False
    for finder in sys.meta_path:
        if isinstance(finder, PackAliasFinder) or type(finder).__name__ == "PackAliasFinder":
            if finder.real_name == real_name:
                return True
            if finder.real_name in sys.modules:
                return False                                 # a first copy is live; leave its aliases alone
            sys.meta_path.remove(finder)
            break
    sys.meta_path.insert(0, PackAliasFinder(real_name))
    for alias in ALIASES:
        if alias != real_name:
            sys.modules[alias] = module
    return True
