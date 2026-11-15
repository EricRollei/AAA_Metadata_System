"""
eric_metadata_save_image_v100.py
Metadata Save Image v1.0 - saves images with automatically collected,
catalog-searchable metadata.

Nothing needs wiring except the image: prompt, models, LoRAs, sampler settings
and seeds are collected from the running workflow, written to the standard
fields Lightroom / XnView / Capture One search (description, keywords,
headline, instructions) and kept in full in the file's own record.

Successor to MetadataAwareSaveImage_v099d and MetadataAwareSaveImage_Simple,
which stay installed so existing workflows keep loading.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
import os
import uuid

import folder_paths
from comfy.cli_args import args
from comfy_api.latest import IO

from ..aaa_meta import color
from ..aaa_meta.fields import UserFields
from ..aaa_meta.pixels import to_pil
from ..aaa_meta.runtime import record_for_node
from ..aaa_meta.save_core import EXTENSIONS, SaveOptions, describe_result, save_image

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")
_BROWSER_PREVIEWABLE = ("png", "jpg", "webp")


def _fill_tokens(prefix: str, record) -> str:
    """%model% and %seed% in the filename prefix."""
    if "%model%" in prefix:
        base = record.base_models[0].stem if record is not None and record.base_models else "model"
        prefix = prefix.replace("%model%", "".join(c if c.isalnum() or c in "._-" else "_" for c in base)[:80])
    if "%seed%" in prefix:
        seed = record.seed if record is not None else None
        prefix = prefix.replace("%seed%", str(seed) if seed is not None else "noseed")
    return prefix


class MetadataAwareSaveImageV100(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="MetadataAwareSaveImage_v100",
            display_name="Metadata Save Image v1.0",
            description=("Saves images with automatically collected generation metadata that Lightroom, XnView "
                         "and Capture One can search: prompt as description, model / LoRA / sampler as keywords."),
            category="Eric's Nodes/Output",
            search_aliases=["save", "save image", "metadata", "xmp", "lightroom"],
            inputs=[
                IO.Image.Input("images", tooltip="The images to save."),
                IO.String.Input("filename_prefix", default="ComfyUI",
                                tooltip="File name prefix; may include a subfolder. Tokens: %model%, %seed%, "
                                        "%date:yyyy-MM-dd%, %width%, %height%."),
                IO.DynamicCombo.Input(
                    "format",
                    options=[
                        IO.DynamicCombo.Option("png", [
                            IO.Combo.Input("bit_depth", options=["8-bit", "16-bit"], default="8-bit",
                                           tooltip="16-bit is written from the full-precision image data."),
                            IO.Int.Input("compress_level", default=4, min=0, max=9, advanced=True,
                                         tooltip="0 = fastest and largest, 9 = slowest and smallest. Lossless either way."),
                        ]),
                        IO.DynamicCombo.Option("jpg", [
                            IO.Int.Input("quality", default=95, min=1, max=100),
                        ]),
                        IO.DynamicCombo.Option("webp", [
                            IO.Int.Input("quality", default=95, min=1, max=100),
                            IO.Boolean.Input("lossless", default=False),
                        ]),
                        IO.DynamicCombo.Option("tiff", [
                            IO.Combo.Input("bit_depth", options=["8-bit", "16-bit"], default="16-bit"),
                            IO.Combo.Input("compression", options=["deflate", "lzw", "none"], default="deflate",
                                           advanced=True),
                        ]),
                    ],
                    tooltip="File format. Capture One does not import WebP.",
                ),
                IO.Combo.Input("color_profile", options=color.PROFILE_CHOICES, default=color.PROFILE_SRGB,
                               tooltip="Colour space of the saved file. Other than sRGB, the pixels are converted "
                                       "and the matching ICC profile is embedded."),
                IO.String.Input("title", default="", tooltip="Optional title."),
                IO.String.Input("keywords", default="", tooltip="Your own keywords, comma separated. Model, LoRA "
                                                                "and sampler keywords are added automatically."),
                IO.String.Input("creator", default="", tooltip="Optional creator / author name."),
                IO.String.Input("copyright", default="", tooltip="Optional copyright notice."),
                IO.Boolean.Input("embed_metadata", default=True,
                                 tooltip="Off: save pixels only (no prompt, record, keywords or workflow)."),
                IO.Boolean.Input("embed_workflow", default=True, advanced=True,
                                 tooltip="Embed the ComfyUI workflow so the file can be dragged back into ComfyUI (PNG)."),
                IO.Boolean.Input("embed_a1111", default=True, advanced=True,
                                 tooltip="Also write the A1111-style parameters text that Civitai reads."),
                IO.Combo.Input("hash_models", options=["cached", "compute", "off"], default="cached", advanced=True,
                               tooltip="cached: use hashes already known. compute: also hash unknown model files "
                                       "(slow once per large file). off: no hashes."),
                IO.Boolean.Input("include_model_paths", default=False, advanced=True,
                                 tooltip="Keep the full disk paths of model files in the embedded record."),
                IO.Boolean.Input("save_sidecar", default=False, advanced=True,
                                 tooltip="Also write a .xmp file next to the image (XnView and Capture One read it; "
                                         "Lightroom does not)."),
            ],
            hidden=[IO.Hidden.prompt, IO.Hidden.extra_pnginfo, IO.Hidden.unique_id, IO.Hidden.dynprompt],
            is_output_node=True,
            outputs=[
                IO.Image.Output(display_name="images"),
                IO.String.Output(display_name="file_path"),
                IO.String.Output(display_name="summary"),
            ],
        )

    @classmethod
    def execute(cls, images, filename_prefix: str, format: dict, color_profile: str, title: str, keywords: str,
                creator: str, copyright: str, embed_metadata: bool, embed_workflow: bool, embed_a1111: bool,
                hash_models: str, include_model_paths: bool, save_sidecar: bool) -> IO.NodeOutput:
        file_format = format["format"]
        metadata_on = embed_metadata and not args.disable_metadata
        prompt = cls.hidden.prompt
        extra_pnginfo = cls.hidden.extra_pnginfo

        record = None
        if metadata_on:
            record = record_for_node(cls.hidden.unique_id, prompt, cls.hidden.dynprompt, hash_models)
            record.height, record.width = int(images.shape[1]), int(images.shape[2])

        png_chunks = {}
        if metadata_on and embed_workflow:
            if prompt is not None:
                png_chunks["prompt"] = json.dumps(prompt)
            for key, value in (extra_pnginfo or {}).items():
                png_chunks[key] = json.dumps(value)

        options = SaveOptions(
            file_format=file_format,
            bit_depth=16 if format.get("bit_depth") == "16-bit" else 8,
            quality=int(format.get("quality", 95)),
            lossless=bool(format.get("lossless", False)),
            compress_level=int(format.get("compress_level", 4)),
            tiff_compression=str(format.get("compression", "deflate")),
            color_profile=color_profile,
            profile_dir=PROFILE_DIR,
            embed_metadata=metadata_on,
            embed_workflow=embed_workflow,
            embed_a1111=embed_a1111,
            include_model_paths=include_model_paths,
            sidecar=save_sidecar,
            png_chunks=png_chunks,
        )
        user = UserFields(title=title, creator=creator, copyright=copyright,
                          keywords=[k.strip() for k in keywords.split(",") if k.strip()])

        prefix = _fill_tokens(filename_prefix, record)
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            prefix, folder_paths.get_output_directory(), images[0].shape[1], images[0].shape[0])

        ui_images = []
        summaries = []
        first_path = ""
        for batch_number, image in enumerate(images):
            name = filename.replace("%batch_num%", str(batch_number))
            file = f"{name}_{counter:05}.{EXTENSIONS[file_format]}"
            path = os.path.join(full_output_folder, file)
            pixels = image.cpu().numpy()
            result = save_image(pixels, path, options, record=record, user=user)
            summaries.append(describe_result(result))
            first_path = first_path or path
            if file_format in _BROWSER_PREVIEWABLE:
                ui_images.append({"filename": file, "subfolder": subfolder, "type": "output"})
            else:
                preview = f"aaa_preview_{uuid.uuid4().hex[:12]}.png"
                to_pil(pixels[..., :3]).save(os.path.join(folder_paths.get_temp_directory(), preview), compress_level=1)
                ui_images.append({"filename": preview, "subfolder": "", "type": "temp"})
            counter += 1

        summary = "\n".join(summaries)
        if record is not None:
            summary += "\n\n" + record.summary()
        return IO.NodeOutput(images, first_path, summary, ui={"images": ui_images})


NODE_CLASS_MAPPINGS = {"MetadataAwareSaveImage_v100": MetadataAwareSaveImageV100}
NODE_DISPLAY_NAME_MAPPINGS = {"MetadataAwareSaveImage_v100": "Metadata Save Image v1.0"}
