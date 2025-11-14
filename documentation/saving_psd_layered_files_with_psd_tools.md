Saving Layered PSD Files with Python (Layers, Transparency, ICC Profile & Metadata)
Using psd-tools for Layered PSDs
psd-tools provides a high-level API to create PSDs with multiple layers. You can create a new PSD document and append layers as PixelLayer objects. Each layer can be named and have its blend mode and opacity adjusted via the API. For example, the code uses:
overlay_layer.blend_mode = BlendMode.SCREEN (using BlendMode constants) and overlay_layer.opacity = 128 to set blend mode and opacity​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. These correspond to Photoshop’s layer blend modes and opacity and will be honored in Photoshop when the PSD is opened.
Named layers: You can assign to layer.name to label the layer (e.g. main_layer.name = "Main Image"). Photoshop will display this name on the layer.
Blend modes: Use the constants in psd_tools.constants.BlendMode (e.g. BlendMode.NORMAL, BlendMode.MULTIPLY) and assign to layer.blend_mode. This ensures the correct blend mode is saved​
FILE-CJCWTSYPRNLALU2F3PUCCQ
.
Opacity: The layer.opacity property accepts 0–255 (representing 0–100% opacity). Setting this will preserve the layer’s transparency level​
FILE-CJCWTSYPRNLALU2F3PUCCQ
.
Preserving per-layer transparency: By default, if the PSD document is created in RGB mode, any alpha channel in your image may be flattened (transparent areas can turn black) when saving​
GITHUB.COM
. To correctly preserve pixel transparency (the alpha channel) for each layer, you should create the PSD in RGBA mode. In practice:
Initialize the PSD with an alpha channel: psd = PSDImage.new(mode='RGBA', size=(width, height)). This ensures the document supports transparency​
GITHUB.COM
.
Convert source images to RGBA before creating the PixelLayer. For example:
python
Copy
Edit
if pil_img.mode != 'RGBA':
    pil_img = pil_img.convert('RGBA')
layer = PixelLayer.frompil(pil_img, psd)
psd.append(layer)
This way, the PixelLayer.frompil will include the image’s alpha channel. With the PSD in RGBA mode, transparent regions remain transparent (not filled with black)​
GITHUB.COM
. This approach is simpler than manually adding layer masks for transparency.
Layer masks: Photoshop layer masks (separate grayscale masks attached to layers) are a bit tricky with psd-tools. The library does support a mask property on layers (for “user mask” data). In the current implementation, the code attempts main_layer.mask.set(alpha_channel) for the main image​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. This attaches the image’s alpha as a layer mask. If you need to attach an external mask image to a layer, you can do something similar: create a PixelLayer for the layer’s content, then call layer.mask.set(mask_image). However, psd-tools doesn’t provide high-level methods to attach a separate mask easily – this would require ensuring the mask image is a single-channel (mode 'L') and using internal APIs. If attaching complex masks is critical and psd-tools falls short, consider using an alternative library (discussed below) or include the mask as its own layer (as done in the code for “mask layers”). In the provided code, “mask_layer_1” and “mask_layer_2” are added as ordinary layers containing the mask imagery (converted to grayscale)​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. This means they appear as separate grayscale layers in Photoshop (not attached masks), which may be acceptable depending on the use-case. True attached layer masks per layer would need more low-level handling.
Embedding ICC Color Profile in the PSD
Embedding the correct ICC profile is essential for color fidelity. By default, psd-tools will not embed any ICC profile unless you add it to the PSD’s image resources. Photoshop will assume a profile (often sRGB) if none is embedded. To embed a profile:
Load the ICC profile bytes (e.g. from an .icc file for “Adobe RGB”, “sRGB v4”, etc.). In the code, color_profile_data = self._get_color_profile(name) accomplishes this (reading the profile file into bytes)​
FILE-CJCWTSYPRNLALU2F3PUCCQ
.
Insert this into the PSD’s image resources with the ICC profile resource ID (ID 1039). psd-tools exposes psd.image_resources, which is a dict-like container for image resources (color profiles, EXIF data, XMP, etc.)​
PSD-TOOLS.READTHEDOCS.IO
​
PSD-TOOLS.READTHEDOCS.IO
. In psd-tools 1.x, you may need to use internal APIs to add a resource. One approach (used in the code) is constructing an ImageResource object:
python
Copy
Edit
from psd_tools.constants import Resource
from psd_tools.psd.image_resources import ImageResource, ImageResources
# Ensure the PSD has an image_resources container
if not hasattr(psd._record, 'image_resources'):
    psd._record.image_resources = ImageResources()
icc_res = ImageResource(
    signature=b'8BIM', 
    key=Resource.ICC_PROFILE.value, 
    name='', 
    data=icc_profile_bytes
)
psd._record.image_resources.append(icc_res)
This attaches the ICC profile bytes under the standard Photoshop resource ID for ICC profiles. The provided code used a workaround of saving a PNG with the profile and re-opening it to grab the resource​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
, but the above direct method is simpler. After adding this, Photoshop will recognize the embedded profile. (You can verify by opening the PSD in Photoshop and checking Edit → Assign Profile…, it should show the profile as embedded.)
Note: psd-tools by default might convert images to sRGB on import/export (for example, psd.compose() applies the ICC profile by default​
PSD-TOOLS.READTHEDOCS.IO
). When saving, however, if we manually embed the profile as above, we are ensuring the output file carries the correct ICC tag. No color conversion is done by psd-tools in this process; it’s simply embedding the provided profile data.
Embedding XMP and IPTC Metadata
To preserve image metadata (e.g. prompts, descriptions, or other custom data), the PSD format supports XMP metadata blocks and IPTC/NAA records. psd-tools doesn’t have high-level functions to add metadata, but you can again use image resources:
XMP Metadata (Resource ID 1060): In the code, after saving, they reopen the PSD and create an XMP ImageResource​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. We can integrate that step into the save process itself. First, generate an XMP packet (XML string) from the metadata dictionary. The code’s _metadata_to_xmp_string(metadata) does this, producing an XML <x:xmpmeta> packet. Then embed it:
python
Copy
Edit
xmp_data = xmp_string.encode('utf-8')
xmp_res = ImageResource(b'8BIM', Resource.XMP_METADATA.value, name='', data=xmp_data)
psd._record.image_resources.append(xmp_res)
If an XMP block already exists in the PSD (which it typically wouldn’t in a new file), you would replace it; otherwise, appending is fine​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. This ensures all the metadata (including things like prompts or any fields you encoded into the XMP) is stored in the PSD. Photoshop will read this and populate the File→File Info dialog accordingly.
IPTC metadata (Resource ID 1028): Photoshop also has legacy IPTC/NAA metadata. The code generates a simple IPTC byte payload (_generate_iptc_data) with fields like title, description, keywords, etc., and adds it similarly​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. If you want maximum compatibility, you can do this, but note that IPTC fields are largely also represented in the XMP (XMP is considered the modern standard, and Photoshop will sync common fields between IPTC and XMP). Still, for completeness, you can attach an IPTC resource:
python
Copy
Edit
iptc_res = ImageResource(b'8BIM', Resource.IPTC_NAA.value, name='', data=iptc_bytes)
psd._record.image_resources.append(iptc_res)
(Replace existing if one is present, similar to XMP.)
By adding XMP (and IPTC) before the final psd.save(), you can save the PSD with metadata embedded in one go. This is preferable to the original approach of saving then reopening to inject metadata. It reduces the chance of something going wrong in that second step and ensures the file on disk is final. Important: Make sure to perform these image resource modifications before calling psd.save(). Once you call psd.save(path), the in-memory PSD is written to disk. In the provided implementation, they did psd.save() then _embed_metadata_in_psd(). You can refactor so that all necessary resources (ICC, XMP, IPTC) are in place, then call save() once. This will produce a PSD that Photoshop opens with correct layers, profiles, and metadata.
Handling 16-bit Depth Requirements
One major limitation is 16-bit per channel support. The PSD format does support 16-bit and 32-bit depth, but psd-tools (as of its current version) does not reliably support writing 16-bit PSDs. In fact, the code logs a note: “16-bit PSD is not fully supported by psd-tools… Consider using TIFF format for 16-bit images.”​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. In practice, if you attempt to use psd-tools to write a 16-bit PSD, it will either downsample to 8-bit or produce a file Photoshop can’t interpret properly at 16-bit depth. Workarounds/Alternatives for 16-bit:
Use a high-bit TIFF: TIFF is a format that supports 16-bit color depth and can also contain layers. Photoshop can honor layers in a TIFF and treat it almost like a PSD​
STACKOVERFLOW.COM
. In fact, if you save a layered image as TIFF in Photoshop with “Save Layers” on, the layers are preserved. The downside is that creating a truly layered TIFF programmatically is complex – PIL’s TIFF support is limited to multipage images (which Photoshop won’t interpret as layers in the same way) and doesn’t directly support Photoshop’s private layer data tags. However, the tifffile library (and others like OpenImageIO or pyvips) can write multi-layer or multi-channel TIFFs. Advanced usage of tifffile has shown that one can embed multiple images and alpha channels such that Photoshop loads them as layers or alpha channels​
STACKOVERFLOW.COM
​
STACKOVERFLOW.COM
. This is not trivial, but it’s an option. If your priority is preserving 16-bit color and metadata over layer editability, another approach is simply saving a flat 16-bit TIFF alongside the layered 8-bit PSD. The TIFF can carry the ICC profile and all metadata (TIFF supports embedding ICC, XMP, IPTC easily), and the PSD carries the layer structure for reference. Photoshop will use the TIFF for high-quality data and you still have the PSD layers if needed.
Use a different Python PSD library: An alternative library called pytoshop (by mdboom) is specifically designed to read and write PSD/PSB files​
GITHUB.COM
. Unlike psd-tools (which started primarily as a reader), pytoshop gives you more low-level control to specify bit depth, color mode, and channels for each layer. You construct layers by supplying numpy arrays for each channel (including 16-bit arrays for high depth images) and then write out a PSD. For example, using pytoshop’s nested_layers API, you can do:
python
Copy
Edit
from pytoshop.user import nested_layers
# ... build a list of nested_layers.Image objects for each layer ...
psd_data = nested_layers.nested_layers_to_psd(layers_list, color_mode=enums.ColorMode.RGB, depth=enums.ColorDepth sixteenBits)
with open("output.psd", "wb") as f:
    psd_data.write(f)
This will create a PSD with the specified depth (e.g. 16-bit) and all your layers. You can include layer masks, adjustment layers, etc., but of course you must construct them with the library’s tools. Pytoshop is lower-level; you have to manually provide the pixel data for each layer and manage things like group hierarchy. The upside is that it can produce a fully spec-compliant PSD with 16-bit channels, embedded profiles, and metadata (you can add ICC profiles and XMP through its image_resources similar to psd-tools, since it’s based on the spec). If psd-tools cannot meet your needs for 16-bit, pytoshop is a viable alternative​
PYPI.ORG
 – it’s actively intended for PSD writing. The trade-off is more coding effort.
Recommendation: If you only occasionally need 16-bit and mostly care about final image fidelity, use TIFF for those cases (perhaps output a TIFF when 16-bit is selected, as the code already hints). If you need layered 16-bit images, consider implementing a path with pytoshop for those cases. In any case, communicate to the user (or in documentation) that Photoshop compatibility for 16-bit images is best achieved via TIFF or a specialized library, since standard psd-tools PSD output will be 8-bit​
FILE-CJCWTSYPRNLALU2F3PUCCQ
.
Summary of Code Changes to Fix Issues
To implement the above in the provided ComfyUI node code, here are the concrete edits and best practices:
Preserve transparency in saved PSD: Initialize the PSD with RGBA mode and include alpha channels for layers. In _save_as_psd, change:
python
Copy
Edit
psd = PSDImage.new(mode='RGB', size=(width, height))
to:
python
Copy
Edit
psd = PSDImage.new(mode='RGBA', size=(width, height))
Also remove the manual has_alpha check and mask application for the main layer​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. Instead, always convert the PIL image to 'RGBA' (if not already) and do PixelLayer.frompil(image_rgba, psd). Do the same for any overlay images: ensure they’re 'RGBA' before creating the PixelLayer. This way, the alpha channel is inherently part of the layer data. The GitHub issue confirming this fix showed that creating the PSD in RGBA mode keeps transparent areas intact​
GITHUB.COM
​
GITHUB.COM
. After this change, you should find that your PSD, when opened in Photoshop, has no unwanted black backgrounds on semi-transparent PNG content (the transparent pixels remain transparent).
Layer masks (if needed): If the goal is to attach provided mask images as layer masks in Photoshop (rather than as separate mask image layers), psd-tools doesn’t offer a simple one-liner. One approach could be: after adding a normal layer, create a mask via layer.mask property. For example, layer.mask = psd_tools.api.mask.Mask(width, height) and then layer.mask.top = layer.mask.left = 0; layer.mask.data = mask_bytes. However, this is an advanced use of psd-tools internal API (and not thoroughly documented). Given the complexity, the simpler route taken in the code — adding mask images as regular layers named “Mask 1”, etc. — is acceptable. Those layers can be set to a specific blend mode (e.g. “normal” or “multiply”) depending on how you intend to use them in Photoshop. If they should just be reference masks, keeping them hidden or in a group might be wise. In short, ensure the mask layers are added after the main image layer, with appropriate names, and possibly locked or grouped, so that they don’t inadvertently obscure the main image. (No code change needed if this behavior is intended, but it’s a design consideration.)
Embed ICC profile correctly: Remove the temporary PNG file hack used to import the ICC profile​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. Instead, use the approach described earlier to append the ICC profile bytes to psd.image_resources. In code, right after assembling the layers (and before saving), do something like:
python
Copy
Edit
if color_profile_data:
    if not hasattr(psd._record, 'image_resources'):
        psd._record.image_resources = ImageResources()
    icc_res = ImageResource(b'8BIM', Resource.ICC_PROFILE.value, name='', data=color_profile_data)
    psd._record.image_resources.append(icc_res)
    print(f"[PSD] Embedded ICC profile: {color_profile_name}")
You’ve already loaded color_profile_data (in the code it’s stored in metadata['__icc_profile_data'] as well). By appending it to the PSD’s resources, it will be written into the file. This change ensures the resulting PSD has the correct ICC tag (you can verify by opening the PSD in an ICC-aware viewer or Photoshop – the colors should appear correct and the profile should be listed).
Embed metadata (XMP/IPTC) correctly: Instead of calling _embed_metadata_in_psd after saving, integrate that logic before saving. You can actually call that function on the in-memory psd object by slight modification (or copy its code). Essentially: construct xmp_data = self._metadata_to_xmp_string(metadata)​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
, then do the ImageResource creation for XMP (Resource 1060) and IPTC (1028) as shown in the function​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. Do this prior to saving. For example:
python
Copy
Edit
if metadata:
    xmp_str = self._metadata_to_xmp_string(metadata)
    xmp_bytes = xmp_str.encode('utf-8')
    # Ensure image_resources exists (as done above)
    psd._record.image_resources.append(
        ImageResource(b'8BIM', Resource.XMP_METADATA.value, name='', data=xmp_bytes)
    )
    iptc_data = self._generate_iptc_data(metadata)
    if iptc_data:
        psd._record.image_resources.append(
            ImageResource(b'8BIM', Resource.IPTC_NAA.value, name='', data=iptc_data)
        )
Then simply call psd.save(image_path). This embeds the metadata in one pass. You should also remove or bypass the existing post-save metadata embedding code to avoid duplication. The result is that your PSD will contain the metadata internally. Photoshop can retrieve it (check File Info → Raw Data to see the XMP block). This addresses the issue where previously the metadata may not have been preserved if something went wrong in the post-save step. By doing it all in-memory, you increase reliability.
16-bit depth option fixes: In the node UI, it says “16-bit only works with PNG.” To enforce this, you might explicitly guard against PSD+16-bit. For instance, if file_format == "psd" and bit_depth == "16-bit", either automatically downgrade to 8-bit with a warning, or better, present an error to the user. Since the code already prints a warning when saving PSD with 16-bit​
FILE-CJCWTSYPRNLALU2F3PUCCQ
, you could expand that. For example, when the user selects PSD and 16-bit, you could internally switch to saving a TIFF:
python
Copy
Edit
if file_format == "psd" and bit_depth == "16-bit":
    print("[Note] PSD format does not support 16-bit in this node; saving as TIFF instead for fidelity.")
    file_format = "tiff"
and then proceed with TIFF saving logic. This way, the user still gets a 16-bit file with layers (if possible) or at least the full image. Another approach is to use pytoshop when 16-bit PSD is requested: this is more involved (would require integrating pytoshop just for that path), so switching to TIFF is simpler. In any case, make sure the user’s intent is respected – if they specifically want a layered PSD and 16-bit data, inform them of the limitation clearly. The best practice here is transparency with the user: it’s better to give a high-quality TIFF than a PSD that looks correct but is secretly 8-bit. And indeed, Photoshop will treat a layered TIFF very much like a PSD in most cases​
STACKOVERFLOW.COM
.
Consider alternative libraries for full fidelity: If down the road you need features like adjustment layers, vector masks, 16/32-bit depth, etc., that psd-tools cannot handle, consider migrating to a more specialized PSD library or even Adobe’s official APIs. For example, as mentioned, pytoshop can create complex PSDs. The usage is a bit different (you assemble layer data manually). A snippet from a community example:
python
Copy
Edit
layer = nested_layers.Image(name="Layer 1", visible=True, opacity=255, blend_mode=enums.BlendMode.normal,
                            top=0, left=0, channels=[R_array, G_array, B_array, A_array], color_mode=enums.ColorMode.RGB)
layers = [layer, ...]  # list of all layer objects
psd_file = nested_layers.nested_layers_to_psd(layers, color_mode=enums.ColorMode.RGB)
with open("out.psd", "wb") as f:
    psd_file.write(f)
GIST.GITHUB.COM
. This produces a PSD with those layers and channels (you can specify 16-bit by using 16-bit numpy arrays and the appropriate ColorDepth). Such an approach would preserve everything at the cost of more code. It’s an option if you find psd-tools limiting. Otherwise, sticking with psd-tools and the TIFF workaround for 16-bit is usually sufficient for compatibility.
In summary, by making the above changes you will: ensure layer transparency is maintained correctly, embed the color profile and metadata into the PSD for Photoshop to read, and handle the 16-bit case more gracefully. The result should be a PSD (or TIFF for 16-bit) that opens in Adobe Photoshop with all layers named and blended correctly, full per-pixel transparency, the correct colors (no shift, thanks to ICC), and all your metadata (XMP/IPTC) visible in Photoshop’s info panels. These adjustments maximize fidelity and compatibility with Photoshop’s expectations for layered files. Lastly, always test the output in Photoshop (and possibly other tools) to confirm everything is preserved as intended. PSD is a complex format, and what works in one library version might have quirks – but following the official resource IDs and standards as we did above is the best way to ensure a robust result. With these best practices, you’ll be saving images with a quality on par with Photoshop’s own “Save As PSD” output, as well as working around the limitations of the libraries where needed (using TIFF or alternative libraries for special cases)​
FILE-CJCWTSYPRNLALU2F3PUCCQ
​
STACKOVERFLOW.COM
. Sources: The implementation details and limitations discussed are based on the psd-tools documentation and issues, as well as community insights. For example, psd-tools maintainers note that writing 16-bit PSDs isn’t supported and suggest using TIFF for those cases​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. Photoshop’s handling of TIFF as an alternative is mentioned by experts: “Photoshop honours TIFF layers and pretty much treats TIFFs as near equals to PSD files.”​
STACKOVERFLOW.COM
. The strategy for preserving transparency by using an RGBA mode PSD comes from a reported solution in the psd-tools GitHub issues​
GITHUB.COM
​
GITHUB.COM
. The approach to embed ICC profiles and XMP/IPTC metadata is derived from the PSD format specification (resource IDs 1039, 1060, 1028) and the psd-tools API usage shown in the code​
PSD-TOOLS.READTHEDOCS.IO
​
FILE-CJCWTSYPRNLALU2F3PUCCQ
. Finally, the existence of the pytoshop library for writing PSDs is noted in its documentation (it explicitly supports reading/writing PSD/PSB)​
PYPI.ORG
, which can be a fallback for features beyond psd-tools’ scope. By integrating these insights, the node will reliably produce Photoshop-compatible files with all desired attributes preserved.