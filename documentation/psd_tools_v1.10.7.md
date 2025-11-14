psd_tools library information

>>> print(psd_tools.__version__)
1.10.7
>>>

>>> print(dir(psd_tools))
['PSDImage', '__all__', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', '__version__', 'api', 'compression', 'constants', 'psd', 'terminology', 'utils', 'validators', 'version']
>>> print(dir(psd_tools.api))
['__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', 'adjustments', 'deprecated', 'effects', 'functools', 'layers', 'mask', 'numpy_io', 'pil_io', 'psd_image', 'shape', 'smart_object', 'warnings']



>>> print(dir(psd_tools.PSDImage))
['__abstractmethods__', '__annotations__', '__class__', '__class_getitem__', '__delattr__', '__delitem__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__getstate__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__len__', '__lt__', '__module__', '__ne__', '__new__', '__parameters__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setitem__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__weakref__', '_abc_impl', '_bbox', '_check_valid_layers', '_clear_clipping_layers', '_compute_clipping_layers', '_get_pattern', '_init', '_is_protocol', '_is_runtime_protocol', '_make_header', '_repr_pretty_', '_update_layer_metadata', '_update_psd_record', '_update_record', 'append', 'bbox', 'bottom', 'channels', 'clear', 'color_mode', 'compatibility_mode', 'composite', 'count', 'depth', 'descendants', 'extend', 'find', 'findall', 'frompil', 'has_preview', 'has_thumbnail', 'height', 'image_resources', 'index', 'insert', 'is_group', 'is_visible', 'kind', 'left', 'name', 'new', 'numpy', 'offset', 'open', 'parent', 'pil_mode', 'pop', 'remove', 'right', 'save', 'size', 'tagged_blocks', 'thumbnail', 'top', 'topil', 'version', 'viewbox', 'visible', 'width']



>>> print(help(psd_tools.api.layers))
Help on module psd_tools.api.layers in psd_tools.api:

NAME
    psd_tools.api.layers - Layer module.

CLASSES
    builtins.object
        Layer
            AdjustmentLayer
            FillLayer
            PixelLayer
            ShapeLayer
            SmartObjectLayer
            TypeLayer
    typing.Protocol(typing.Generic)
        GroupMixin
            Group(GroupMixin, Layer)
                Artboard

    class AdjustmentLayer(Layer)
     |  AdjustmentLayer(*args: 'Any')
     |
     |  Layer that applies specified image adjustment effect.
     |
     |  Method resolution order:
     |      AdjustmentLayer
     |      Layer
     |      builtins.object
     |
     |  Methods defined here:
     |
     |  __init__(self, *args: 'Any')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image` or `None`.
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

    class Artboard(Group)
     |  Artboard(psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |
     |  Artboard is a special kind of group that has a pre-defined viewbox.
     |
     |  Method resolution order:
     |      Artboard
     |      Group
     |      GroupMixin
     |      typing.Protocol
     |      typing.Generic
     |      Layer
     |      builtins.object
     |
     |  Methods defined here:
     |
     |  __subclasshook__ = _proto_hook(other)
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties defined here:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __abstractmethods__ = frozenset()
     |
     |  __annotations__ = {}
     |
     |  __parameters__ = ()
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Group:
     |
     |  __init__(self, psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True)
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image`.
     |
     |  ----------------------------------------------------------------------
     |  Class methods inherited from Group:
     |
     |  group_layers(layers: 'list[Layer]', name: 'str' = 'Group', parent: 'GroupMixin | None' = None, open_folder: 'bool' = True) from typing._ProtocolMeta
     |      Create a new Group object containing the given layers and moved into the parent folder.
     |
     |      If no parent is provided, the group will be put in place of the first layer in the given list. Example below:
     |
     |      :param layers: The layers to group. Can by any subclass of :py:class:`~psd_tools.api.layers.Layer`
     |      :param name: The display name of the group. Default to "Group".
     |      :param parent: The parent group to add the newly created Group object into.
     |      :param open_folder: Boolean defining whether the folder will be open or closed in photoshop. Default to True.
     |
     |      :return: A :py:class:`~psd_tools.api.layers.Group`
     |
     |  new(name: 'str' = 'Group', open_folder: 'bool' = True, parent: 'GroupMixin | None' = None) -> 'Self' from typing._ProtocolMeta
     |      Create a new Group object with minimal records and data channels and metadata to properly include the group in the PSD file.
     |
     |      :param name: The display name of the group. Default to "Group".
     |      :param open_folder: Boolean defining whether the folder will be open or closed in photoshop. Default to True.
     |      :param parent: Optional parent folder to move the newly created group into.
     |
     |      :return: A :py:class:`~psd_tools.api.layers.Group` object
     |
     |  ----------------------------------------------------------------------
     |  Static methods inherited from Group:
     |
     |  extract_bbox(layers, include_invisible: 'bool' = False) -> 'tuple[int, int, int, int]'
     |      Returns a bounding box for ``layers`` or (0, 0, 0, 0) if the layers
     |      have no bounding box.
     |
     |      :param include_invisible: include invisible layers in calculation.
     |      :return: tuple of four int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Group:
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from GroupMixin:
     |
     |  __delitem__(self, key) -> 'None'
     |
     |  __getitem__(self, key) -> 'Layer'
     |
     |  __iter__(self) -> 'Iterator[Layer]'
     |
     |  __len__(self) -> 'int'
     |
     |  __setitem__(self, key, value) -> 'None'
     |
     |  append(self, layer: 'Layer') -> 'None'
     |      Add a layer to the end (top) of the group
     |
     |      :param layer: The layer to add
     |
     |  clear(self) -> 'None'
     |      Clears the group.
     |
     |  count(self, layer: 'Layer') -> 'int'
     |      Counts the number of occurences of a layer in the group.
     |
     |      :param layer:
     |
     |  descendants(self, include_clip: 'bool' = True) -> 'Iterator[Layer]'
     |      Return a generator to iterate over all descendant layers.
     |
     |      Example::
     |
     |          # Iterate over all layers
     |          for layer in psd.descendants():
     |              print(layer)
     |
     |          # Iterate over all layers in reverse order
     |          for layer in reversed(list(psd.descendants())):
     |              print(layer)
     |
     |      :param include_clip: include clipping layers.
     |
     |  extend(self, layers: 'Iterable[Layer]') -> 'None'
     |      Add a list of layers to the end (top) of the group
     |
     |      :param layers: The layers to add
     |
     |  find(self, name: 'str') -> 'Layer | None'
     |      Returns the first layer found for the given layer name
     |
     |      :param name:
     |
     |  findall(self, name: 'str') -> 'Iterator[Layer]'
     |      Return a generator to iterate over all layers with the given name.
     |
     |      :param name:
     |
     |  index(self, layer: 'Layer') -> 'int'
     |      Returns the index of the specified layer in the group.
     |
     |      :param layer:
     |
     |  insert(self, index: 'int', layer: 'Layer') -> 'None'
     |      Insert the given layer at the specified index.
     |
     |      :param index:
     |      :param layer:
     |
     |  pop(self, index: 'int' = -1) -> 'Layer'
     |      Removes the specified layer from the list and returns it.
     |
     |      :param index:
     |
     |  remove(self, layer: 'Layer') -> 'Self'
     |      Removes the specified layer from the group
     |
     |      :param layer:
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from GroupMixin:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  ----------------------------------------------------------------------
     |  Class methods inherited from typing.Protocol:
     |
     |  __init_subclass__(*args, **kwargs) from typing._ProtocolMeta
     |      This method is called when a class is subclassed.
     |
     |      The default implementation does nothing. It may be
     |      overridden to extend subclasses.
     |
     |  ----------------------------------------------------------------------
     |  Class methods inherited from typing.Generic:
     |
     |  __class_getitem__(params) from typing._ProtocolMeta
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

    class FillLayer(Layer)
     |  FillLayer(*args: 'Any')
     |
     |  Layer that fills the canvas region.
     |
     |  Method resolution order:
     |      FillLayer
     |      Layer
     |      builtins.object
     |
     |  Methods defined here:
     |
     |  __init__(self, *args: 'Any')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties defined here:
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __annotations__ = {}
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image` or `None`.
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

    class Group(GroupMixin, Layer)
     |  Group(psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |
     |  Group of layers.
     |
     |  Example::
     |
     |      group = psd[1]
     |      for layer in group:
     |          if layer.kind == 'pixel':
     |              print(layer.name)
     |
     |  Method resolution order:
     |      Group
     |      GroupMixin
     |      typing.Protocol
     |      typing.Generic
     |      Layer
     |      builtins.object
     |
     |  Methods defined here:
     |
     |  __init__(self, psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  __subclasshook__ = _proto_hook(other)
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True)
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image`.
     |
     |  ----------------------------------------------------------------------
     |  Class methods defined here:
     |
     |  group_layers(layers: 'list[Layer]', name: 'str' = 'Group', parent: 'GroupMixin | None' = None, open_folder: 'bool' = True) from typing._ProtocolMeta
     |      Create a new Group object containing the given layers and moved into the parent folder.
     |
     |      If no parent is provided, the group will be put in place of the first layer in the given list. Example below:
     |
     |      :param layers: The layers to group. Can by any subclass of :py:class:`~psd_tools.api.layers.Layer`
     |      :param name: The display name of the group. Default to "Group".
     |      :param parent: The parent group to add the newly created Group object into.
     |      :param open_folder: Boolean defining whether the folder will be open or closed in photoshop. Default to True.
     |
     |      :return: A :py:class:`~psd_tools.api.layers.Group`
     |
     |  new(name: 'str' = 'Group', open_folder: 'bool' = True, parent: 'GroupMixin | None' = None) -> 'Self' from typing._ProtocolMeta
     |      Create a new Group object with minimal records and data channels and metadata to properly include the group in the PSD file.
     |
     |      :param name: The display name of the group. Default to "Group".
     |      :param open_folder: Boolean defining whether the folder will be open or closed in photoshop. Default to True.
     |      :param parent: Optional parent folder to move the newly created group into.
     |
     |      :return: A :py:class:`~psd_tools.api.layers.Group` object
     |
     |  ----------------------------------------------------------------------
     |  Static methods defined here:
     |
     |  extract_bbox(layers, include_invisible: 'bool' = False) -> 'tuple[int, int, int, int]'
     |      Returns a bounding box for ``layers`` or (0, 0, 0, 0) if the layers
     |      have no bounding box.
     |
     |      :param include_invisible: include invisible layers in calculation.
     |      :return: tuple of four int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __abstractmethods__ = frozenset()
     |
     |  __annotations__ = {}
     |
     |  __parameters__ = ()
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from GroupMixin:
     |
     |  __delitem__(self, key) -> 'None'
     |
     |  __getitem__(self, key) -> 'Layer'
     |
     |  __iter__(self) -> 'Iterator[Layer]'
     |
     |  __len__(self) -> 'int'
     |
     |  __setitem__(self, key, value) -> 'None'
     |
     |  append(self, layer: 'Layer') -> 'None'
     |      Add a layer to the end (top) of the group
     |
     |      :param layer: The layer to add
     |
     |  clear(self) -> 'None'
     |      Clears the group.
     |
     |  count(self, layer: 'Layer') -> 'int'
     |      Counts the number of occurences of a layer in the group.
     |
     |      :param layer:
     |
     |  descendants(self, include_clip: 'bool' = True) -> 'Iterator[Layer]'
     |      Return a generator to iterate over all descendant layers.
     |
     |      Example::
     |
     |          # Iterate over all layers
     |          for layer in psd.descendants():
     |              print(layer)
     |
     |          # Iterate over all layers in reverse order
     |          for layer in reversed(list(psd.descendants())):
     |              print(layer)
     |
     |      :param include_clip: include clipping layers.
     |
     |  extend(self, layers: 'Iterable[Layer]') -> 'None'
     |      Add a list of layers to the end (top) of the group
     |
     |      :param layers: The layers to add
     |
     |  find(self, name: 'str') -> 'Layer | None'
     |      Returns the first layer found for the given layer name
     |
     |      :param name:
     |
     |  findall(self, name: 'str') -> 'Iterator[Layer]'
     |      Return a generator to iterate over all layers with the given name.
     |
     |      :param name:
     |
     |  index(self, layer: 'Layer') -> 'int'
     |      Returns the index of the specified layer in the group.
     |
     |      :param layer:
     |
     |  insert(self, index: 'int', layer: 'Layer') -> 'None'
     |      Insert the given layer at the specified index.
     |
     |      :param index:
     |      :param layer:
     |
     |  pop(self, index: 'int' = -1) -> 'Layer'
     |      Removes the specified layer from the list and returns it.
     |
     |      :param index:
     |
     |  remove(self, layer: 'Layer') -> 'Self'
     |      Removes the specified layer from the group
     |
     |      :param layer:
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from GroupMixin:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |
     |  left
     |
     |  right
     |
     |  top
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from GroupMixin:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  ----------------------------------------------------------------------
     |  Class methods inherited from typing.Protocol:
     |
     |  __init_subclass__(*args, **kwargs) from typing._ProtocolMeta
     |      This method is called when a class is subclassed.
     |
     |      The default implementation does nothing. It may be
     |      overridden to extend subclasses.
     |
     |  ----------------------------------------------------------------------
     |  Class methods inherited from typing.Generic:
     |
     |  __class_getitem__(params) from typing._ProtocolMeta
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

    class GroupMixin(typing.Protocol)
     |  GroupMixin(*args, **kwargs)
     |
     |  Method resolution order:
     |      GroupMixin
     |      typing.Protocol
     |      typing.Generic
     |      builtins.object
     |
     |  Methods defined here:
     |
     |  __delitem__(self, key) -> 'None'
     |
     |  __getitem__(self, key) -> 'Layer'
     |
     |  __init__ = _no_init_or_replace_init(self, *args, **kwargs)
     |
     |  __iter__(self) -> 'Iterator[Layer]'
     |
     |  __len__(self) -> 'int'
     |
     |  __setitem__(self, key, value) -> 'None'
     |
     |  __subclasshook__ = _proto_hook(other)
     |
     |  append(self, layer: 'Layer') -> 'None'
     |      Add a layer to the end (top) of the group
     |
     |      :param layer: The layer to add
     |
     |  clear(self) -> 'None'
     |      Clears the group.
     |
     |  count(self, layer: 'Layer') -> 'int'
     |      Counts the number of occurences of a layer in the group.
     |
     |      :param layer:
     |
     |  descendants(self, include_clip: 'bool' = True) -> 'Iterator[Layer]'
     |      Return a generator to iterate over all descendant layers.
     |
     |      Example::
     |
     |          # Iterate over all layers
     |          for layer in psd.descendants():
     |              print(layer)
     |
     |          # Iterate over all layers in reverse order
     |          for layer in reversed(list(psd.descendants())):
     |              print(layer)
     |
     |      :param include_clip: include clipping layers.
     |
     |  extend(self, layers: 'Iterable[Layer]') -> 'None'
     |      Add a list of layers to the end (top) of the group
     |
     |      :param layers: The layers to add
     |
     |  find(self, name: 'str') -> 'Layer | None'
     |      Returns the first layer found for the given layer name
     |
     |      :param name:
     |
     |  findall(self, name: 'str') -> 'Iterator[Layer]'
     |      Return a generator to iterate over all layers with the given name.
     |
     |      :param name:
     |
     |  index(self, layer: 'Layer') -> 'int'
     |      Returns the index of the specified layer in the group.
     |
     |      :param layer:
     |
     |  insert(self, index: 'int', layer: 'Layer') -> 'None'
     |      Insert the given layer at the specified index.
     |
     |      :param index:
     |      :param layer:
     |
     |  pop(self, index: 'int' = -1) -> 'Layer'
     |      Removes the specified layer from the list and returns it.
     |
     |      :param index:
     |
     |  remove(self, layer: 'Layer') -> 'Self'
     |      Removes the specified layer from the group
     |
     |      :param layer:
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties defined here:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |
     |  left
     |
     |  right
     |
     |  top
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __abstractmethods__ = frozenset()
     |
     |  __annotations__ = {'_bbox': 'tuple[int, int, int, int] | None', '_laye...
     |
     |  __parameters__ = ()
     |
     |  ----------------------------------------------------------------------
     |  Class methods inherited from typing.Protocol:
     |
     |  __init_subclass__(*args, **kwargs) from typing._ProtocolMeta
     |      This method is called when a class is subclassed.
     |
     |      The default implementation does nothing. It may be
     |      overridden to extend subclasses.
     |
     |  ----------------------------------------------------------------------
     |  Class methods inherited from typing.Generic:
     |
     |  __class_getitem__(params) from typing._ProtocolMeta

    class Layer(builtins.object)
     |  Layer(psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |
     |  Methods defined here:
     |
     |  __init__(self, psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image` or `None`.
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties defined here:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __annotations__ = {}

    class PixelLayer(Layer)
     |  PixelLayer(psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |
     |  Layer that has rasterized image in pixels.
     |
     |  Example::
     |
     |      assert layer.kind == 'pixel':
     |      image = layer.composite()
     |      image.save('layer.png')
     |
     |  Method resolution order:
     |      PixelLayer
     |      Layer
     |      builtins.object
     |
     |  Class methods defined here:
     |
     |  frompil(pil_im: 'PILImage', psd_file: 'Any | None' = None, layer_name: 'str' = 'Layer', top: 'int' = 0, left: 'int' = 0, compression: 'Compression' = <Compression.RLE: 1>, **kwargs: 'Any') -> "'PixelLayer'" from builtins.type
     |      Creates a PixelLayer from a PIL image for a given psd file.
     |
     |      :param pil_im: The :py:class:`~PIL.Image` object to convert to photoshop
     |      :param psdfile: The psd file the image will be converted for.
     |      :param layer_name: The name of the layer. Defaults to "Layer"
     |      :param top: Pixelwise offset from the top of the canvas for the new layer.
     |      :param left: Pixelwise offset from the left of the canvas for the new layer.
     |      :param compression: Compression algorithm to use for the data.
     |
     |      :return: A :py:class:`~psd_tools.api.layers.PixelLayer` object
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __annotations__ = {}
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __init__(self, psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image` or `None`.
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

    class ShapeLayer(Layer)
     |  ShapeLayer(*args: 'Any')
     |
     |  Layer that has drawing in vector mask.
     |
     |  Method resolution order:
     |      ShapeLayer
     |      Layer
     |      builtins.object
     |
     |  Methods defined here:
     |
     |  __init__(self, *args: 'Any')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties defined here:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __annotations__ = {}
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image` or `None`.
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

    class SmartObjectLayer(Layer)
     |  SmartObjectLayer(psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |
     |  Layer that inserts external data.
     |
     |  Use :py:attr:`~psd_tools.api.layers.SmartObjectLayer.smart_object`
     |  attribute to get the external data. See
     |  :py:class:`~psd_tools.api.smart_object.SmartObject`.
     |
     |  Example::
     |
     |      import io
     |      if layer.smart_object.filetype == 'jpg':
     |          image = Image.open(io.BytesIO(layer.smart_object.data))
     |
     |  Method resolution order:
     |      SmartObjectLayer
     |      Layer
     |      builtins.object
     |
     |  Readonly properties defined here:
     |
     |  smart_object
     |      Associated smart object.
     |
     |      :return: :py:class:`~psd_tools.api.smart_object.SmartObject`.
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __annotations__ = {}
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __init__(self, psd: 'Any', record: 'LayerRecord', channels: 'ChannelDataList', parent: 'TGroupMixin | None')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image` or `None`.
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

    class TypeLayer(Layer)
     |  TypeLayer(*args: 'Any')
     |
     |  Layer that has text and styling information for fonts or paragraphs.
     |
     |  Text is accessible at :py:attr:`~psd_tools.api.layers.TypeLayer.text`
     |  property. Styling information for paragraphs is in
     |  :py:attr:`~psd_tools.api.layers.TypeLayer.engine_dict`.
     |  Document styling information such as font list is is
     |  :py:attr:`~psd_tools.api.layers.TypeLayer.resource_dict`.
     |
     |  Currently, textual information is read-only.
     |
     |  Example::
     |
     |      if layer.kind == 'type':
     |          print(layer.text)
     |          print(layer.engine_dict['StyleRun'])
     |
     |          # Extract font for each substring in the text.
     |          text = layer.engine_dict['Editor']['Text'].value
     |          fontset = layer.resource_dict['FontSet']
     |          runlength = layer.engine_dict['StyleRun']['RunLengthArray']
     |          rundata = layer.engine_dict['StyleRun']['RunArray']
     |          index = 0
     |          for length, style in zip(runlength, rundata):
     |              substring = text[index:index + length]
     |              stylesheet = style['StyleSheet']['StyleSheetData']
     |              font = fontset[stylesheet['Font']]
     |              print('%r gets %s' % (substring, font))
     |              index += length
     |
     |  Method resolution order:
     |      TypeLayer
     |      Layer
     |      builtins.object
     |
     |  Methods defined here:
     |
     |  __init__(self, *args: 'Any')
     |      Initialize self.  See help(type(self)) for accurate signature.
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties defined here:
     |
     |  document_resources
     |      Resource set relevant to the document.
     |
     |  engine_dict
     |      Styling information dict.
     |
     |  resource_dict
     |      Resource set.
     |
     |  text
     |      Text in the layer. Read-only.
     |
     |      .. note:: New-line character in Photoshop is `'\\r'`.
     |
     |  text_type
     |      Text type. Read-only.
     |
     |      :return:
     |       - :py:attr:`psd_tools.constants.TextType.POINT` for point type text (also known as character type)
     |       - :py:attr:`psd_tools.constants.TextType.PARAGRAPH` for paragraph type text (also known as area type)
     |       - `None` if text type cannot be determined or information is unavailable
     |
     |      See :py:class:`psd_tools.constants.TextType`.
     |
     |  transform
     |      Matrix (xx, xy, yx, yy, tx, ty) applies affine transformation.
     |
     |  warp
     |      Warp configuration.
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __annotations__ = {}
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from Layer:
     |
     |  __repr__(self) -> 'str'
     |      Return repr(self).
     |
     |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...] | np.ndarray' = 1.0, alpha: 'float | np.ndarray' = 0.0, layer_filter: 'Callable | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Composite layer and masks (mask, vector mask, and clipping layers).
     |
     |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
     |          tuple. Default is the layer's bbox.
     |      :param force: Boolean flag to force vector drawing.
     |      :param color: Backdrop color specified by scalar or tuple of scalar.
     |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
     |          specifies red in RGB color mode.
     |      :param alpha: Backdrop alpha in [0.0, 1.0].
     |      :param layer_filter: Callable that takes a layer as argument and
     |          returns whether if the layer is composited. Default is
     |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
     |      :return: :py:class:`PIL.Image` or `None`.
     |
     |  delete_layer(self) -> 'Self'
     |      Deletes the layer and all its child layers if the layer is a group from its parent (group or psdimage).
     |
     |  has_clip_layers(self) -> 'bool'
     |      Returns True if the layer has associated clipping.
     |
     |      :return: `bool`
     |
     |  has_effects(self) -> 'bool'
     |      Returns True if the layer has effects.
     |
     |      :return: `bool`
     |
     |  has_mask(self) -> 'bool'
     |      Returns True if the layer has a mask.
     |
     |      :return: `bool`
     |
     |  has_origination(self) -> 'bool'
     |      Returns True if the layer has live shape properties.
     |
     |      :return: `bool`
     |
     |  has_pixels(self) -> 'bool'
     |      Returns True if the layer has associated pixels. When this is True,
     |      `topil` method returns :py:class:`PIL.Image`.
     |
     |      :return: `bool`
     |
     |  has_stroke(self) -> 'bool'
     |      Returns True if the shape has a stroke.
     |
     |  has_vector_mask(self) -> 'bool'
     |      Returns True if the layer has a vector mask.
     |
     |      :return: `bool`
     |
     |  is_group(self) -> 'bool'
     |      Return True if the layer is a group.
     |
     |      :return: `bool`
     |
     |  is_visible(self) -> 'bool'
     |      Layer visibility. Takes group visibility in account.
     |
     |      :return: `bool`
     |
     |  lock(self, lock_flags: 'int' = <ProtectedFlags.COMPLETE: 2147483648>) -> 'None'
     |      Locks a layer accordind to the combination of flags.
     |
     |      :param lockflags: An integer representing the locking state
     |
     |      Example using the constants of ProtectedFlags and bitwise or operation to lock both pixels and positions::
     |
     |          layer.lock(ProtectedFlags.COMPOSITE | ProtectedFlags.POSITION)
     |
     |  move_down(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer down a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  move_to_group(self, group: "'GroupMixin'") -> 'Self'
     |      Moves the layer to the given group, updates the tree metadata as needed.
     |
     |      :param group: The group the current layer will be moved into.
     |
     |  move_up(self, offset: 'int' = 1) -> 'Self'
     |      Moves the layer up a certain offset within the group the layer is in.
     |
     |      :param offset:
     |
     |  numpy(self, channel: 'str | None' = None, real_mask: 'bool' = True) -> 'np.ndarray | None'
     |      Get NumPy array of the layer.
     |
     |      :param channel: Which channel to return, can be 'color',
     |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
     |      :return: :py:class:`numpy.ndarray` or None if there is no pixel.
     |
     |  topil(self, channel: 'int | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
     |      Get PIL Image of the layer.
     |
     |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
     |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
     |          the method returns all the channels supported by PIL modes.
     |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
     |      :return: :py:class:`PIL.Image`, or `None` if the layer has no pixels.
     |
     |      Example::
     |
     |          from psd_tools.constants import ChannelID
     |
     |          image = layer.topil()
     |          red = layer.topil(ChannelID.CHANNEL_0)
     |          alpha = layer.topil(ChannelID.TRANSPARENCY_MASK)
     |
     |      .. note:: Not all of the PSD image modes are supported in
     |          :py:class:`PIL.Image`. For example, 'CMYK' mode cannot include
     |          alpha channel in PIL. In this case, topil drops alpha channel.
     |
     |  unlock(self) -> 'None'
     |
     |  ----------------------------------------------------------------------
     |  Readonly properties inherited from Layer:
     |
     |  bbox
     |      (left, top, right, bottom) tuple.
     |
     |  bottom
     |      Bottom coordinate.
     |
     |      :return: int
     |
     |  clip_layers
     |      Clip layers associated with this layer.
     |
     |      :return: list of layers
     |
     |  effects
     |      Layer effects.
     |
     |      :return: :py:class:`~psd_tools.api.effects.Effects`
     |
     |  height
     |      Height of the layer.
     |
     |      :return: int
     |
     |  kind
     |      Kind of this layer, such as group, pixel, shape, type, smartobject,
     |      or psdimage. Class name without `layer` suffix.
     |
     |      :return: `str`
     |
     |  layer_id
     |      Layer ID.
     |
     |      :return: int layer id. if the layer is not assigned an id, -1.
     |
     |  locks
     |
     |  mask
     |      Returns mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.mask.Mask` or `None`
     |
     |  origination
     |      Property for a list of live shapes or a line.
     |
     |      Some of the vector masks have associated live shape properties, that
     |      are Photoshop feature to handle primitive shapes such as a rectangle,
     |      an ellipse, or a line. Vector masks without live shape properties are
     |      plain path objects.
     |
     |      See :py:mod:`psd_tools.api.shape`.
     |
     |      :return: List of :py:class:`~psd_tools.api.shape.Invalidated`,
     |          :py:class:`~psd_tools.api.shape.Rectangle`,
     |          :py:class:`~psd_tools.api.shape.RoundedRectangle`,
     |          :py:class:`~psd_tools.api.shape.Ellipse`, or
     |          :py:class:`~psd_tools.api.shape.Line`.
     |
     |  parent
     |      Parent of this layer.
     |
     |  right
     |      Right coordinate.
     |
     |      :return: int
     |
     |  size
     |      (width, height) tuple.
     |
     |      :return: `tuple`
     |
     |  stroke
     |      Property for strokes.
     |
     |  tagged_blocks
     |      Layer tagged blocks that is a dict-like container of settings.
     |
     |      See :py:class:`psd_tools.constants.Tag` for available
     |      keys.
     |
     |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks`.
     |
     |      Example::
     |
     |          from psd_tools.constants import Tag
     |          metadata = layer.tagged_blocks.get_data(Tag.METADATA_SETTING)
     |
     |  vector_mask
     |      Returns vector mask associated with this layer.
     |
     |      :return: :py:class:`~psd_tools.api.shape.VectorMask` or `None`
     |
     |  width
     |      Width of the layer.
     |
     |      :return: int
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from Layer:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
     |
     |  blend_mode
     |      Blend mode of this layer. Writable.
     |
     |      Example::
     |
     |          from psd_tools.constants import BlendMode
     |          if layer.blend_mode == BlendMode.NORMAL:
     |              layer.blend_mode = BlendMode.SCREEN
     |
     |      :return: :py:class:`~psd_tools.constants.BlendMode`.
     |
     |  clipping_layer
     |      Clipping flag for this layer. Writable.
     |
     |      :return: `bool`
     |
     |  left
     |      Left coordinate. Writable.
     |
     |      :return: int
     |
     |  name
     |      Layer name. Writable.
     |
     |      :return: `str`
     |
     |  offset
     |      (left, top) tuple. Writable.
     |
     |      :return: `tuple`
     |
     |  opacity
     |      Opacity of this layer in [0, 255] range. Writable.
     |
     |      :return: int
     |
     |  top
     |      Top coordinate. Writable.
     |
     |      :return: int
     |
     |  visible
     |      Layer visibility. Doesn't take group visibility in account. Writable.
     |
     |      :return: `bool`

DATA
    Callable = typing.Callable
        Deprecated alias to collections.abc.Callable.

        Callable[[int], str] signifies a function that takes a single
        parameter of type int and returns a str.

        The subscription syntax must always be used with exactly two
        values: the argument list and the return type.
        The argument list must be a list of types, a ParamSpec,
        Concatenate or ellipsis. The return type must be a single type.

        There is no syntax to indicate optional or keyword arguments;
        such function types are rarely used as callback types.

    Iterable = typing.Iterable
        A generic version of collections.abc.Iterable.

    Iterator = typing.Iterator
        A generic version of collections.abc.Iterator.

    Self = typing.Self
    TGroupMixin = ~TGroupMixin
    logger = <Logger psd_tools.api.layers (WARNING)>

FILE
    a:\comfy_dec\python_embeded\lib\site-packages\psd_tools\api\layers.py


None
>>> print(help(psd_tools.PSDImage))
Help on class PSDImage in module psd_tools.api.psd_image:

class PSDImage(psd_tools.api.layers.GroupMixin)
 |  PSDImage(data: 'PSD')
 |
 |  Photoshop PSD/PSB file object.
 |
 |  The low-level data structure is accessible at :py:attr:`PSDImage._record`.
 |
 |  Example::
 |
 |      from psd_tools import PSDImage
 |
 |      psd = PSDImage.open('example.psd')
 |      image = psd.compose()
 |
 |      for layer in psd:
 |          layer_image = layer.compose()
 |
 |  Method resolution order:
 |      PSDImage
 |      psd_tools.api.layers.GroupMixin
 |      typing.Protocol
 |      typing.Generic
 |      builtins.object
 |
 |  Methods defined here:
 |
 |  __init__(self, data: 'PSD')
 |      Initialize self.  See help(type(self)) for accurate signature.
 |
 |  __repr__(self) -> 'str'
 |      Return repr(self).
 |
 |  __subclasshook__ = _proto_hook(other)
 |
 |  composite(self, viewport: 'tuple[int, int, int, int] | None' = None, force: 'bool' = False, color: 'float | tuple[float, ...]' = 1.0, alpha: 'float' = 0.0, layer_filter: 'Callable | None' = None, ignore_preview: 'bool' = False, apply_icc: 'bool' = True)
 |      Composite the PSD image.
 |
 |      :param viewport: Viewport bounding box specified by (x1, y1, x2, y2)
 |          tuple. Default is the viewbox of the PSD.
 |      :param ignore_preview: Boolean flag to whether skip compositing when a
 |          pre-composited preview is available.
 |      :param force: Boolean flag to force vector drawing.
 |      :param color: Backdrop color specified by scalar or tuple of scalar.
 |          The color value should be in [0.0, 1.0]. For example, (1., 0., 0.)
 |          specifies red in RGB color mode.
 |      :param alpha: Backdrop alpha in [0.0, 1.0].
 |      :param layer_filter: Callable that takes a layer as argument and
 |          returns whether if the layer is composited. Default is
 |          :py:func:`~psd_tools.api.layers.PixelLayer.is_visible`.
 |      :return: :py:class:`PIL.Image`.
 |
 |  has_preview(self) -> 'bool'
 |      Returns if the document has real merged data. When True, `topil()`
 |      returns pre-composed data.
 |
 |  has_thumbnail(self) -> 'bool'
 |      True if the PSDImage has a thumbnail resource.
 |
 |  is_group(self) -> 'bool'
 |      Return True if the layer is a group.
 |
 |      :return: `bool`
 |
 |  is_visible(self) -> 'bool'
 |      Returns visibility of the element.
 |
 |      :return: `bool`
 |
 |  numpy(self, channel: "Literal['color', 'shape', 'alpha', 'mask'] | None" = None) -> 'np.ndarray'
 |      Get NumPy array of the layer.
 |
 |      :param channel: Which channel to return, can be 'color',
 |          'shape', 'alpha', or 'mask'. Default is 'color+alpha'.
 |      :return: :py:class:`numpy.ndarray`
 |
 |  save(self, fp: 'BinaryIO | str | bytes | os.PathLike', mode: 'str' = 'wb', **kwargs: 'Any') -> 'None'
 |      Save the PSD file. Updates the ImageData section if the layer structure has been updated.
 |
 |      :param fp: filename or file-like object.
 |      :param encoding: charset encoding of the pascal string within the file,
 |          default 'macroman'.
 |      :param mode: file open mode, default 'wb'.
 |
 |  thumbnail(self) -> 'PILImage | None'
 |      Returns a thumbnail image in PIL.Image. When the file does not
 |      contain an embedded thumbnail image, returns None.
 |
 |  topil(self, channel: 'int | ChannelID | None' = None, apply_icc: 'bool' = True) -> 'PILImage | None'
 |      Get PIL Image.
 |
 |      :param channel: Which channel to return; e.g., 0 for 'R' channel in RGB
 |          image. See :py:class:`~psd_tools.constants.ChannelID`. When `None`,
 |          the method returns all the channels supported by PIL modes.
 |      :param apply_icc: Whether to apply ICC profile conversion to sRGB.
 |      :return: :py:class:`PIL.Image`, or `None` if the composed image is not
 |          available.
 |
 |  ----------------------------------------------------------------------
 |  Class methods defined here:
 |
 |  frompil(image: 'PILImage', compression=<Compression.RLE: 1>) -> 'Self' from typing._ProtocolMeta
 |      Create a new PSD document from PIL Image.
 |
 |      :param image: PIL Image object.
 |      :param compression: ImageData compression option. See
 |          :py:class:`~psd_tools.constants.Compression`.
 |      :return: A :py:class:`~psd_tools.api.psd_image.PSDImage` object.
 |
 |  new(mode: 'str', size: 'tuple[int, int]', color: 'int' = 0, depth: 'Literal[8, 16, 32]' = 8, **kwargs: 'Any') from typing._ProtocolMeta
 |      Create a new PSD document.
 |
 |      :param mode: The color mode to use for the new image.
 |      :param size: A tuple containing (width, height) in pixels.
 |      :param color: What color to use for the image. Default is black.
 |      :return: A :py:class:`~psd_tools.api.psd_image.PSDImage` object.
 |
 |  open(fp: 'BinaryIO | str | bytes | os.PathLike', **kwargs: 'Any') -> 'Self' from typing._ProtocolMeta
 |      Open a PSD document.
 |
 |      :param fp: filename or file-like object.
 |      :param encoding: charset encoding of the pascal string within the file,
 |          default 'macroman'. Some psd files need explicit encoding option.
 |      :return: A :py:class:`~psd_tools.api.psd_image.PSDImage` object.
 |
 |  ----------------------------------------------------------------------
 |  Readonly properties defined here:
 |
 |  bbox
 |      Minimal bounding box that contains all the visible layers.
 |
 |      Use :py:attr:`~psd_tools.api.psd_image.PSDImage.viewbox` to get
 |      viewport bounding box. When the psd is empty, bbox is equal to the
 |      canvas bounding box.
 |
 |      :return: (left, top, right, bottom) `tuple`.
 |
 |  bottom
 |      Bottom coordinate.
 |
 |      :return: `int`
 |
 |  channels
 |      Number of color channels.
 |
 |      :return: `int`
 |
 |  color_mode
 |      Document color mode, such as 'RGB' or 'GRAYSCALE'. See
 |      :py:class:`~psd_tools.constants.ColorMode`.
 |
 |      :return: :py:class:`~psd_tools.constants.ColorMode`
 |
 |  depth
 |      Pixel depth bits.
 |
 |      :return: `int`
 |
 |  height
 |      Document height.
 |
 |      :return: `int`
 |
 |  image_resources
 |      Document image resources.
 |      :py:class:`~psd_tools.psd.image_resources.ImageResources` is a
 |      dict-like structure that keeps various document settings.
 |
 |      See :py:class:`psd_tools.constants.Resource` for available keys.
 |
 |      :return: :py:class:`~psd_tools.psd.image_resources.ImageResources`
 |
 |      Example::
 |
 |          from psd_tools.constants import Resource
 |          version_info = psd.image_resources.get_data(Resource.VERSION_INFO)
 |          slices = psd.image_resources.get_data(Resource.SLICES)
 |
 |      Image resources contain an ICC profile. The following shows how to
 |      export a PNG file with embedded ICC profile::
 |
 |          from psd_tools.constants import Resource
 |          icc_profile = psd.image_resources.get_data(Resource.ICC_PROFILE)
 |          image = psd.compose(apply_icc=False)
 |          image.save('output.png', icc_profile=icc_profile)
 |
 |  kind
 |      Kind.
 |
 |      :return: `'psdimage'`
 |
 |  left
 |      Left coordinate.
 |
 |      :return: `0`
 |
 |  name
 |      Element name.
 |
 |      :return: `'Root'`
 |
 |  offset
 |      (left, top) tuple.
 |
 |      :return: `tuple`
 |
 |  parent
 |      Parent of this layer.
 |
 |  pil_mode
 |
 |  right
 |      Right coordinate.
 |
 |      :return: `int`
 |
 |  size
 |      (width, height) tuple.
 |
 |      :return: `tuple`
 |
 |  tagged_blocks
 |      Document tagged blocks that is a dict-like container of settings.
 |
 |      See :py:class:`psd_tools.constants.Tag` for available
 |      keys.
 |
 |      :return: :py:class:`~psd_tools.psd.tagged_blocks.TaggedBlocks` or
 |          `None`.
 |
 |      Example::
 |
 |          from psd_tools.constants import Tag
 |          patterns = psd.tagged_blocks.get_data(Tag.PATTERNS1)
 |
 |  top
 |      Top coordinate.
 |
 |      :return: `0`
 |
 |  version
 |      Document version. PSD file is 1, and PSB file is 2.
 |
 |      :return: `int`
 |
 |  viewbox
 |      Return bounding box of the viewport.
 |
 |      :return: (left, top, right, bottom) `tuple`.
 |
 |  visible
 |      Visibility.
 |
 |      :return: `True`
 |
 |  width
 |      Document width.
 |
 |      :return: `int`
 |
 |  ----------------------------------------------------------------------
 |  Data descriptors defined here:
 |
 |  compatibility_mode
 |      Set the compositing and layer organization compatibility mode. Writable.
 |
 |      :return: :py:class:`~psd_tools.constants.CompatibilityMode`
 |
 |  ----------------------------------------------------------------------
 |  Data and other attributes defined here:
 |
 |  __abstractmethods__ = frozenset()
 |
 |  __annotations__ = {}
 |
 |  __parameters__ = ()
 |
 |  ----------------------------------------------------------------------
 |  Methods inherited from psd_tools.api.layers.GroupMixin:
 |
 |  __delitem__(self, key) -> 'None'
 |
 |  __getitem__(self, key) -> 'Layer'
 |
 |  __iter__(self) -> 'Iterator[Layer]'
 |
 |  __len__(self) -> 'int'
 |
 |  __setitem__(self, key, value) -> 'None'
 |
 |  append(self, layer: 'Layer') -> 'None'
 |      Add a layer to the end (top) of the group
 |
 |      :param layer: The layer to add
 |
 |  clear(self) -> 'None'
 |      Clears the group.
 |
 |  count(self, layer: 'Layer') -> 'int'
 |      Counts the number of occurences of a layer in the group.
 |
 |      :param layer:
 |
 |  descendants(self, include_clip: 'bool' = True) -> 'Iterator[Layer]'
 |      Return a generator to iterate over all descendant layers.
 |
 |      Example::
 |
 |          # Iterate over all layers
 |          for layer in psd.descendants():
 |              print(layer)
 |
 |          # Iterate over all layers in reverse order
 |          for layer in reversed(list(psd.descendants())):
 |              print(layer)
 |
 |      :param include_clip: include clipping layers.
 |
 |  extend(self, layers: 'Iterable[Layer]') -> 'None'
 |      Add a list of layers to the end (top) of the group
 |
 |      :param layers: The layers to add
 |
 |  find(self, name: 'str') -> 'Layer | None'
 |      Returns the first layer found for the given layer name
 |
 |      :param name:
 |
 |  findall(self, name: 'str') -> 'Iterator[Layer]'
 |      Return a generator to iterate over all layers with the given name.
 |
 |      :param name:
 |
 |  index(self, layer: 'Layer') -> 'int'
 |      Returns the index of the specified layer in the group.
 |
 |      :param layer:
 |
 |  insert(self, index: 'int', layer: 'Layer') -> 'None'
 |      Insert the given layer at the specified index.
 |
 |      :param index:
 |      :param layer:
 |
 |  pop(self, index: 'int' = -1) -> 'Layer'
 |      Removes the specified layer from the list and returns it.
 |
 |      :param index:
 |
 |  remove(self, layer: 'Layer') -> 'Self'
 |      Removes the specified layer from the group
 |
 |      :param layer:
 |
 |  ----------------------------------------------------------------------
 |  Data descriptors inherited from psd_tools.api.layers.GroupMixin:
 |
 |  __dict__
 |      dictionary for instance variables (if defined)
 |
 |  __weakref__
 |      list of weak references to the object (if defined)
 |
 |  ----------------------------------------------------------------------
 |  Class methods inherited from typing.Protocol:
 |
 |  __init_subclass__(*args, **kwargs) from typing._ProtocolMeta
 |      This method is called when a class is subclassed.
 |
 |      The default implementation does nothing. It may be
 |      overridden to extend subclasses.
 |
 |  ----------------------------------------------------------------------
 |  Class methods inherited from typing.Generic:
 |
 |  __class_getitem__(params) from typing._ProtocolMeta