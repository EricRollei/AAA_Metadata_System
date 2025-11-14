PSDImage
classpsd_tools.PSDImage(data: PSD)[source]
Photoshop PSD/PSB file object.

The low-level data structure is accessible at PSDImage._record.

Example:

from psd_tools import PSDImage

psd = PSDImage.open('example.psd')
image = psd.compose()

for layer in psd:
    layer_image = layer.compose()
append(layer: Layer)→ None
Add a layer to the end (top) of the group

Parameters
:
layer – The layer to add

propertybbox: tuple[int, int, int, int]
Minimal bounding box that contains all the visible layers.

Use viewbox to get viewport bounding box. When the psd is empty, bbox is equal to the canvas bounding box.

Returns
:
(left, top, right, bottom) tuple.

 
propertybottom: int
Bottom coordinate.

Returns
:
int

 
propertychannels: int
Number of color channels.

Returns
:
int

clear()→ None
Clears the group.

propertycolor_mode: ColorMode
Document color mode, such as ‘RGB’ or ‘GRAYSCALE’. See ColorMode.

Returns
:
ColorMode

 
propertycompatibility_mode: CompatibilityMode
Set the compositing and layer organization compatibility mode. Writable.

Returns
:
CompatibilityMode

composite(viewport: tuple[int, int, int, int] | None = None, force: bool = False, color: float | tuple[float, ...] = 1.0, alpha: float = 0.0, layer_filter: Callable | None = None, ignore_preview: bool = False, apply_icc: bool = True)[source]
Composite the PSD image.

Parameters
:
viewport – Viewport bounding box specified by (x1, y1, x2, y2) tuple. Default is the viewbox of the PSD.

ignore_preview – Boolean flag to whether skip compositing when a pre-composited preview is available.

force – Boolean flag to force vector drawing.

color – Backdrop color specified by scalar or tuple of scalar. The color value should be in [0.0, 1.0]. For example, (1., 0., 0.) specifies red in RGB color mode.

alpha – Backdrop alpha in [0.0, 1.0].

layer_filter – Callable that takes a layer as argument and returns whether if the layer is composited. Default is is_visible().

Returns
:
PIL.Image.

count(layer: Layer)→ int
Counts the number of occurences of a layer in the group.

Parameters
:
layer

propertydepth: int
Pixel depth bits.

Returns
:
int

descendants(include_clip: bool = True)→ Iterator[Layer]
Return a generator to iterate over all descendant layers.

Example:

# Iterate over all layers
for layer in psd.descendants():
    print(layer)

# Iterate over all layers in reverse order
for layer in reversed(list(psd.descendants())):
    print(layer)
Parameters
:
include_clip – include clipping layers.

extend(layers: Iterable[Layer])→ None
Add a list of layers to the end (top) of the group

Parameters
:
layers – The layers to add

find(name: str)→ Layer | None
Returns the first layer found for the given layer name

Parameters
:
name

findall(name: str)→ Iterator[Layer]
Return a generator to iterate over all layers with the given name.

Parameters
:
name

classmethodfrompil(image: Image, compression=Compression.RLE)→ Self[source]
Create a new PSD document from PIL Image.

Parameters
:
image – PIL Image object.

compression – ImageData compression option. See Compression.

Returns
:
A PSDImage object.

has_preview()→ bool[source]
Returns if the document has real merged data. When True, topil() returns pre-composed data.

has_thumbnail()→ bool[source]
True if the PSDImage has a thumbnail resource.

propertyheight: int
Document height.

Returns
:
int

 
propertyimage_resources: ImageResources
Document image resources. ImageResources is a dict-like structure that keeps various document settings.

See psd_tools.constants.Resource for available keys.

Returns
:
ImageResources

Example:

from psd_tools.constants import Resource
version_info = psd.image_resources.get_data(Resource.VERSION_INFO)
slices = psd.image_resources.get_data(Resource.SLICES)
Image resources contain an ICC profile. The following shows how to export a PNG file with embedded ICC profile:

from psd_tools.constants import Resource
icc_profile = psd.image_resources.get_data(Resource.ICC_PROFILE)
image = psd.compose(apply_icc=False)
image.save('output.png', icc_profile=icc_profile)
index(layer: Layer)→ int
Returns the index of the specified layer in the group.

Parameters
:
layer

insert(index: int, layer: Layer)→ None
Insert the given layer at the specified index.

Parameters
:
index

layer

is_group()→ bool[source]
Return True if the layer is a group.

Returns
:
bool

is_visible()→ bool[source]
Returns visibility of the element.

Returns
:
bool

propertykind: str
Kind.

Returns
:
‘psdimage’

 
propertyleft: int
Left coordinate.

Returns
:
0

 
propertyname: str
Element name.

Returns
:
‘Root’

classmethodnew(mode: str, size: tuple[int, int], color: int = 0, depth: Literal[8, 16, 32] = 8, **kwargs: Any)[source]
Create a new PSD document.

Parameters
:
mode – The color mode to use for the new image.

size – A tuple containing (width, height) in pixels.

color – What color to use for the image. Default is black.

Returns
:
A PSDImage object.

numpy(channel: Literal['color', 'shape', 'alpha', 'mask'] | None = None)→ ndarray[source]
Get NumPy array of the layer.

Parameters
:
channel – Which channel to return, can be ‘color’, ‘shape’, ‘alpha’, or ‘mask’. Default is ‘color+alpha’.

Returns
:
numpy.ndarray

propertyoffset: tuple[int, int]
(left, top) tuple.

Returns
:
tuple

classmethodopen(fp: BinaryIO | str | bytes | PathLike, **kwargs: Any)→ Self[source]
Open a PSD document.

Parameters
:
fp – filename or file-like object.

encoding – charset encoding of the pascal string within the file, default ‘macroman’. Some psd files need explicit encoding option.

Returns
:
A PSDImage object.

propertyparent: None
Parent of this layer.

pop(index: int = -1)→ Layer
Removes the specified layer from the list and returns it.

Parameters
:
index

remove(layer: Layer)→ Self
Removes the specified layer from the group

Parameters
:
layer

propertyright: int
Right coordinate.

Returns
:
int

save(fp: BinaryIO | str | bytes | PathLike, mode: str = 'wb', **kwargs: Any)→ None[source]
Save the PSD file. Updates the ImageData section if the layer structure has been updated.

Parameters
:
fp – filename or file-like object.

encoding – charset encoding of the pascal string within the file, default ‘macroman’.

mode – file open mode, default ‘wb’.

propertysize: tuple[int, int]
(width, height) tuple.

Returns
:
tuple

 
propertytagged_blocks: TaggedBlocks | None
Document tagged blocks that is a dict-like container of settings.

See psd_tools.constants.Tag for available keys.

Returns
:
TaggedBlocks or None.

Example:

from psd_tools.constants import Tag
patterns = psd.tagged_blocks.get_data(Tag.PATTERNS1)
thumbnail()→ Image | None[source]
Returns a thumbnail image in PIL.Image. When the file does not contain an embedded thumbnail image, returns None.

propertytop: int
Top coordinate.

Returns
:
0

topil(channel: int | ChannelID | None = None, apply_icc: bool = True)→ Image | None[source]
Get PIL Image.

Parameters
:
channel – Which channel to return; e.g., 0 for ‘R’ channel in RGB image. See ChannelID. When None, the method returns all the channels supported by PIL modes.

apply_icc – Whether to apply ICC profile conversion to sRGB.

Returns
:
PIL.Image, or None if the composed image is not available.

propertyversion: int
Document version. PSD file is 1, and PSB file is 2.

Returns
:
int

 
propertyviewbox: tuple[int, int, int, int]
Return bounding box of the viewport.

Returns
:
(left, top, right, bottom) tuple.

 
propertyvisible: bool
Visibility.

Returns
:
True

 
propertywidth: int
Document width.

Returns
:
int