"""
eric_metadata_entry_v3.py
Eric's Metadata Entry V3

Same widgets, order and behaviour as the previous version (eric_metadata_entry_v2). The only
change: its metadata service is wrapped so that
  * reads also return what the v2 save node stores (automatically collected
    generation record, measured data)
  * writes also land in the fields Lightroom / XnView / Capture One search and
    in the hcai / eiqa namespaces, adding to what the file already holds

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from .eric_metadata_entry_v2 import EricMetadataEntryNodeV2 as _Previous
from ..aaa_meta.legacy_bridge import CompanionService


class EricMetadataEntryNodeV3(_Previous):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata_service = CompanionService(self.metadata_service)


NODE_CLASS_MAPPINGS = {"Eric_Metadata_Entry_V3": EricMetadataEntryNodeV3}
NODE_DISPLAY_NAME_MAPPINGS = {"Eric_Metadata_Entry_V3": "Eric's Metadata Entry V3"}
