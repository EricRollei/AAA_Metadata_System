"""
eric_metadata_save_image_v100.py
Metadata Save Image v1.0

Every widget, feature and widget ORDER of "Save Image with Metadata v099d" is
kept exactly (output folder modes, filename formats, layers and blend modes,
alpha handling, APNG, SVG, PSD, additional format, txt / db / JSON outputs...).
What changes is underneath:

  * generation data is collected automatically by the v2 capture core (works
    with LLM-written prompts, custom samplers, any LoRA loader) - nothing to wire
  * it is written to the fields Lightroom / XnView / Capture One search
    (description, keywords, headline, instructions) plus the hcai / eiqa
    namespaces, and read back to confirm
  * choosing Adobe RGB, ProPhoto or Display P3 (new choice) converts the pixels
    (the old node only attached the profile)
  * 16-bit TIFF is written from the full-precision data (was 8-bit x 256)

New widgets are appended AFTER the existing ones so nothing moves.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os

import numpy as np
import torch
from PIL import Image

from .eric_metadata_save_image_v099d import MetadataAwareSaveImage as _SaveImageV099d
from ..aaa_meta import color, embed, psd_writer
from ..aaa_meta.layers import build_layers, layer_summary, to_float_array
from ..aaa_meta.legacy_bridge import ServiceBridge, map_color_profile, user_fields_from_widgets
from ..aaa_meta.pixels import save_tiff16
from ..aaa_meta.runtime import (measurements_for_node, recipe_plan_for_node, record_for_frame,
                                record_for_node)

_DISPLAY_P3 = "Display P3"
_LAYER_INPUTS = ("mask_layer_1", "mask_layer_2", "overlay_layer_1", "overlay_layer_2")
_OVERLAY_INPUTS = ("overlay_layer_1", "overlay_layer_2")


class _JpegFormatParams(dict):
    """v099d passes matte_color to its JPEG writer twice (once by name, once inside
    **format_params), which made every JPEG save fail. This dict answers
    format_params["matte_color"] but leaves it out of the ** expansion."""

    def __init__(self, values):
        values = dict(values)
        self._matte_color = values.pop("matte_color", "#FFFFFF")
        super().__init__(values)

    def __missing__(self, key):
        if key == "matte_color":
            return self._matte_color
        raise KeyError(key)


def _convert_tensor(images, profile: str):
    """sRGB image tensor (B,H,W,C) -> same tensor in `profile` colour space."""
    array = images.cpu().numpy() if torch.is_tensor(images) else np.asarray(images)
    converted = color.convert_from_srgb(array[..., :3], profile)
    if array.shape[-1] == 4:
        converted = np.concatenate([converted, array[..., 3:]], axis=-1)
    return torch.from_numpy(np.ascontiguousarray(converted.astype(np.float32)))


class MetadataAwareSaveImageV100(_SaveImageV099d):
    @classmethod
    def INPUT_TYPES(cls):
        types = super().INPUT_TYPES()
        optional = dict(types.get("optional", {}))          # existing widgets keep their order
        for name in ("color_profile", "additional_format_color_profile"):   # one more choice in the same widget
            choices, options = optional[name][0], optional[name][1]
            if _DISPLAY_P3 not in choices:
                extended = [c for c in choices if c != "None"] + [_DISPLAY_P3] + (["None"] if "None" in choices else [])
                optional[name] = (extended, options)
        optional["hash_models"] = (["cached", "compute", "off"], {
            "default": "cached",
            "tooltip": "Model hashes for Civitai: cached = use hashes already known; compute = also hash "
                       "unknown files (slow once per large file); off = none."})
        optional["embed_a1111"] = ("BOOLEAN", {
            "default": True,
            "tooltip": "Also write the A1111-style parameters text that Civitai and AI image browsers read."})
        optional["include_model_paths"] = ("BOOLEAN", {
            "default": False,
            "tooltip": "Keep the full disk paths of model files in the embedded record (off: names and hashes only)."})
        optional["convert_to_color_profile"] = ("BOOLEAN", {
            "default": True,
            "tooltip": "Convert the pixels into the chosen colour profile (Adobe RGB / ProPhoto). Off = attach "
                       "the profile without converting, as v099d did."})
        optional["collect_measurements"] = ("BOOLEAN", {
            "default": True,
            "tooltip": "Store results of analysis nodes (Eric-image-classification: UniPercept, blur, IQA...) that "
                       "worked on this image in this run. No wiring needed; the image just has to pass through "
                       "them, or they read it from a node that feeds this save."})
        types["optional"] = optional
        hidden = dict(types.get("hidden", {}))
        hidden["dynprompt"] = "DYNPROMPT"
        types["hidden"] = hidden
        return types

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "filepath", "summary")
    FUNCTION = "save_with_metadata"
    OUTPUT_NODE = True
    CATEGORY = _SaveImageV099d.CATEGORY
    DESCRIPTION = ("Save images with automatically collected generation metadata that Lightroom, XnView and "
                   "Capture One can search. Same options as v099d.")

    def __init__(self):
        super().__init__()
        self.metadata_service = ServiceBridge(self.metadata_service)
        self._v100_layer_detect_calls = 0
        self._v100_frame_index = -1
        self._v100_srgb_frames = None
        self._v100_main_profile = color.PROFILE_SRGB
        self._v100_notes = []

    # ------------------------------------------------------------------
    def save_with_metadata(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None,
                           unique_id=None, dynprompt=None, **kwargs):
        hash_models = kwargs.pop("hash_models", "cached")
        embed_a1111 = kwargs.pop("embed_a1111", True)
        include_model_paths = kwargs.pop("include_model_paths", False)
        convert_colors = kwargs.pop("convert_to_color_profile", True)
        collect_measurements = kwargs.pop("collect_measurements", True)
        self._v100_layer_detect_calls = 0
        self._v100_frame_index = -1
        self._v100_notes = []
        original_images = images

        # 1. collect the generation record (never blocks the save)
        record = None
        if kwargs.get("enable_metadata", True) and kwargs.get("auto_extract_generation_params", True):
            try:
                record = record_for_node(unique_id, prompt, dynprompt, hash_models)
                if torch.is_tensor(images) and images.ndim == 4:
                    record.height, record.width = int(images.shape[1]), int(images.shape[2])
            except Exception as exc:
                self._v100_notes.append(f"automatic collection failed: {exc!r}")
        measurements = {}
        if collect_measurements and kwargs.get("enable_metadata", True):
            try:
                measurements, measurement_notes = measurements_for_node(unique_id, prompt, dynprompt)
                self._v100_notes.extend(measurement_notes)
            except Exception as exc:
                self._v100_notes.append(f"measurement collection failed: {exc!r}")
        self.metadata_service.begin(record, user_fields_from_widgets(kwargs), include_model_paths, embed_a1111,
                                    measurements)
        # what the generator node itself stated (Krea2 settings, sweep cells): one record per image
        plan, frame_records = None, {}
        if record is not None:
            try:
                plan = recipe_plan_for_node(unique_id, prompt, dynprompt)
            except Exception as exc:
                self._v100_notes.append(f"recipe collection failed: {exc!r}")
        if plan is not None:
            frame_count = int(images.shape[0]) if torch.is_tensor(images) and images.ndim == 4 else 1

            def frame_record(index, _base=record):
                if index not in frame_records:
                    frame_records[index] = record_for_frame(_base, plan, index, frame_count, hash_models)
                return frame_records[index]
            self.metadata_service.record_for_frame = frame_record
            try:
                record = frame_record(0)                    # shown in the summary output
                self.metadata_service.record = record
            except Exception as exc:
                self.metadata_service.record_for_frame = None
                self._v100_notes.append(f"recipe not applied: {exc!r}")

        # 2. real colour conversion (the base class then attaches the matching profile)
        self._v100_main_profile = map_color_profile(kwargs.get("color_profile", ""))
        self._v100_srgb_frames = None
        if convert_colors and self._v100_main_profile in color.CONVERTED_PROFILES:
            try:
                self._v100_srgb_frames = images.cpu().numpy() if torch.is_tensor(images) else np.asarray(images)
                images = _convert_tensor(images, self._v100_main_profile)
                for name in _OVERLAY_INPUTS:
                    if kwargs.get(name) is not None:
                        kwargs[name] = _convert_tensor(kwargs[name], self._v100_main_profile)
            except Exception as exc:
                images = original_images
                self._v100_srgb_frames = None
                self._v100_notes.append(f"colour conversion failed, saved unconverted: {exc!r}")

        # 3. everything else exactly as v099d
        output = super().save_with_metadata(images, filename_prefix=filename_prefix, prompt=prompt,
                                            extra_pnginfo=extra_pnginfo, unique_id=unique_id, **kwargs)

        filepath = ""
        if isinstance(output, dict) and isinstance(output.get("result"), tuple) and len(output["result"]) > 1:
            filepath = output["result"][1] or ""
        lines = []
        if not filepath:
            lines.append("NOTHING WAS SAVED - turn on debug_logging and check the console for the error.")
        bridge_summary = self.metadata_service.summary()
        if bridge_summary:
            lines.append(bridge_summary)
        lines.extend(f"note: {note}" for note in self._v100_notes)
        if measurements:
            lines.append("measurements stored: " + ", ".join(measurements.keys()))
        if plan is not None and plan.is_sweep and len(frame_records) > 1:
            lines.append(f"sweep {plan.sweep_id}: each of the {len(frame_records)} images carries the record of its own cell "
                         f"(the record below is image 1)")
        if record is not None:
            lines.append("")
            lines.append(record.summary())
        summary = "\n".join(lines)
        ui = output.get("ui", {}) if isinstance(output, dict) else {}
        return {"ui": ui, "result": (original_images, filepath, summary)}

    # ------------------------------------------------------------------
    # small corrections to v099d behaviour
    # ------------------------------------------------------------------
    def _detect_layers_and_adjust_format(self, current_format, **kwargs):
        # v099d calls this twice in a row; a format change reported by the second
        # call ran into an undefined variable and aborted the whole save.
        result = super()._detect_layers_and_adjust_format(current_format=current_format, **kwargs)
        self._v100_layer_detect_calls += 1
        if self._v100_layer_detect_calls >= 2:
            return result[0], False, ""
        return result

    def _convert_to_pil(self, image):
        # single-channel inputs (a MASK-shaped tensor, or H x W x 1) made v099d's converter fail
        if torch.is_tensor(image):
            if image.ndim == 4:
                image = image[0]
            if image.ndim == 3 and image.shape[-1] == 1:
                image = image[..., 0]
            elif image.ndim == 3 and image.shape[0] == 1 and image.shape[-1] > 4:
                image = image[0]
        return super()._convert_to_pil(image)

    def _get_color_profile(self, profile_name):
        if profile_name == _DISPLAY_P3:
            return color.display_p3_icc()
        return super()._get_color_profile(profile_name)

    def _get_format_parameters(self, **kwargs):
        params = super()._get_format_parameters(**kwargs)
        # v099d's 8-bit PNG / JPEG / WebP and APNG writers look these up under names that
        # were never passed on, so the widgets had no effect there (profile was always
        # sRGB v4 Appearance, workflow always embedded, APNG always 10 fps / loop forever).
        params["color_profile"] = kwargs.get("color_profile", "sRGB v4 Appearance")
        params["embed_workflow"] = kwargs.get("embed_workflow", True)
        params["quality_preset"] = kwargs.get("quality_preset", "Balanced")
        params["fps"] = params.get("apng_fps", 10)
        params["loops"] = params.get("apng_loops", 0)
        if str(kwargs.get("file_format", "")).lower() in ("jpg", "jpeg"):
            return _JpegFormatParams(params)
        return params

    def generate_sequential_filename(self, *args, **kwargs):
        self._v100_frame_index += 1                      # one call per saved frame
        self.metadata_service.frame_index = max(self._v100_frame_index, 0)
        return super().generate_sequential_filename(*args, **kwargs)

    def _save_as_psd(self, image, image_path, metadata=None, prompt=None, extra_pnginfo=None, **kwargs):
        # v099d writes 8-bit PSDs only. 16-bit: same layer stack, written from the full-precision data.
        if kwargs.get("bit_depth", "8-bit") != "16-bit":
            return super()._save_as_psd(image, image_path, metadata=metadata, prompt=prompt,
                                        extra_pnginfo=extra_pnginfo, **kwargs)
        try:
            layers = build_layers(image, kwargs)
            profile_name = kwargs.get("color_profile", "None")
            icc = self._get_color_profile(profile_name) if profile_name != "None" else None
            psd_writer.write_psd(image_path, to_float_array(image), layers, depth=16, icc_profile=icc)
            if isinstance(metadata, dict):
                metadata.setdefault("analysis", {})["layer_info"] = layer_summary(layers)
                metadata.setdefault("technical", {})["bit_depth"] = "16-bit"
            print(f"[PSD] Saved PSD (16-bit) with {len(layers)} layers to: {image_path}")
            return True
        except Exception as exc:
            self._v100_notes.append(f"16-bit PSD failed ({exc!r}); saved 8-bit with the v099d writer")
            return super()._save_as_psd(image, image_path, metadata=metadata, prompt=prompt,
                                        extra_pnginfo=extra_pnginfo, **kwargs)

    def _add_photoshop_layers_to_tiff(self, image, image_path, widgets):
        """Adds the layer stack in the form Photoshop reads from TIFF files (tag 37724).
        The pages v099d wrote stay as they are, so other programs see what they saw before."""
        with open(image_path, "rb") as handle:
            byte_order = "<" if handle.read(2) == b"II" else ">"
        import tifffile
        with tifffile.TiffFile(image_path) as tif:                 # the layers must match the file's real depth
            depth = 16 if int(tif.pages[0].bitspersample) == 16 else 8
        layers = build_layers(image, widgets)
        block = psd_writer.photoshop_tiff_block(layers, depth, byte_order)
        ok, message = embed.write_binary_tag(image_path, "IFD0:ImageSourceData", block)
        if not ok:
            self._v100_notes.append(f"Photoshop layers not added to the TIFF: {message}")
        return ok

    def _save_as_tiff(self, image, image_path, metadata=None, prompt=None, extra_pnginfo=None, **kwargs):
        # True 16-bit for a plain (no extra layers) TIFF. With layers, v099d's writer is used unchanged.
        has_layers = any(kwargs.get(name) is not None for name in _LAYER_INPUTS)
        if kwargs.get("bit_depth", "8-bit") == "16-bit":
            # True 16-bit from the full-precision data. With layers: the picture plus the layer stack
            # Photoshop reads (v099d's 16-bit conversion of layered TIFFs fails and falls back to 8-bit).
            try:
                profile_name = kwargs.get("color_profile", "sRGB v4 Appearance")
                icc = self._get_color_profile(profile_name) if profile_name != "None" else None
                save_tiff16(to_float_array(image), image_path, None, icc, "deflate")
                if has_layers:
                    self._add_photoshop_layers_to_tiff(image, image_path, kwargs)
                    if isinstance(metadata, dict):
                        metadata.setdefault("analysis", {})["layer_info"] = layer_summary(build_layers(image, kwargs))
                return True
            except Exception as exc:
                self._v100_notes.append(f"true 16-bit TIFF failed, used the v099d writer: {exc!r}")
        saved = super()._save_as_tiff(image, image_path, metadata=metadata, prompt=prompt,
                                      extra_pnginfo=extra_pnginfo, **kwargs)
        if saved and has_layers and os.path.isfile(image_path):
            try:
                self._add_photoshop_layers_to_tiff(image, image_path, kwargs)
            except Exception as exc:
                self._v100_notes.append(f"Photoshop layers not added to the TIFF: {exc!r}")
        return saved

    def _save_as_apng(self, images, image_path, metadata=None, prompt=None, extra_pnginfo=None, **kwargs):
        # v099d needs the optional "apng" package; without it nothing was saved.
        # Pillow writes animated PNG itself, so use that when the old writer gives up.
        try:
            if super()._save_as_apng(images, image_path, metadata=metadata, prompt=prompt,
                                     extra_pnginfo=extra_pnginfo, **kwargs) and os.path.isfile(image_path):
                return True
        except Exception as exc:
            self._v100_notes.append(f"v099d APNG writer failed ({exc!r}); used Pillow")
        try:
            arrays = []
            for item in ([images] if (torch.is_tensor(images) or isinstance(images, np.ndarray)) else list(images)):
                array = item.detach().cpu().numpy() if torch.is_tensor(item) else np.asarray(item)
                arrays.extend(list(array) if array.ndim == 4 else [array])
            pil_frames = [Image.fromarray((np.clip(a.astype(np.float32), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
                          if a.dtype != np.uint8 else Image.fromarray(a) for a in arrays]
            pnginfo = None
            if kwargs.get("embed_workflow", True) and prompt:
                pnginfo = self._prepare_workflow_pnginfo(prompt, extra_pnginfo)
            profile_name = kwargs.get("color_profile", "sRGB v4 Appearance")
            icc = self._get_color_profile(profile_name) if profile_name != "None" else None
            fps = max(float(kwargs.get("fps", 10) or 10), 0.1)
            options = {"format": "PNG", "save_all": True, "append_images": pil_frames[1:],
                       "duration": int(round(1000.0 / fps)), "loop": int(kwargs.get("loops", 0) or 0)}
            if pnginfo is not None:
                options["pnginfo"] = pnginfo
            if icc:
                options["icc_profile"] = icc
            pil_frames[0].save(image_path, **options)
            return True
        except Exception as exc:
            self._v100_notes.append(f"APNG not saved: {exc!r}")
            return False

    def _save_additional_format(self, image, primary_path, metadata, prompt=None, extra_pnginfo=None, **kwargs):
        # The second copy may use a different colour profile than the main file:
        # start again from the sRGB pixels so it is not converted twice.
        if self._v100_srgb_frames is not None:
            additional_profile = map_color_profile(kwargs.get("additional_format_color_profile", ""))
            if additional_profile != self._v100_main_profile:
                index = min(max(self._v100_frame_index, 0), len(self._v100_srgb_frames) - 1)
                image = self._v100_srgb_frames[index]
                if additional_profile in color.CONVERTED_PROFILES:
                    converted = color.convert_from_srgb(image[..., :3], additional_profile)
                    image = np.concatenate([converted, image[..., 3:]], axis=-1) if image.shape[-1] == 4 else converted
        return super()._save_additional_format(image, primary_path, metadata, prompt=prompt,
                                               extra_pnginfo=extra_pnginfo, **kwargs)


NODE_CLASS_MAPPINGS = {"MetadataAwareSaveImage_v100": MetadataAwareSaveImageV100}
NODE_DISPLAY_NAME_MAPPINGS = {"MetadataAwareSaveImage_v100": "Metadata Save Image v1.0"}
