"""
Eric's Civitai Prompt Extractor Node
Loads images, extracts Civitai metadata from EXIF user comments,
and optionally writes the information to a text file.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

import comfy.sd
import comfy.utils
import folder_paths
import node_helpers
import requests


class EricCivitaiPromptExtractor:
    """Load an image, extract Civitai prompts, and expose structured outputs."""

    CATEGORY = "metadata"
    FUNCTION = "load_and_extract"
    RETURN_TYPES = (
        "IMAGE",
        "MASK",
        "STRING",
        "STRING",
        "STRING",
        "STRING",
        "STRING",
        "FLOAT",
        "INT",
        "INT",
        "STRING",
        "STRING",
        "INT",
        "INT",
    )
    RETURN_NAMES = (
        "image",
        "mask",
        "filename",
        "full_path",
        "positive_prompt",
        "negative_prompt",
        "sampler",
        "cfg",
        "seed",
        "clip_skip",
        "resources",
        "raw_exif",
        "file_count",
        "current_index",
    )

    _SUPPORTED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".gif",
        ".tiff",
        ".tif",
        ".webp",
        ".psd",
        ".svg",
    }

    # Track the most recently used index per folder so auto-increment can continue across runs.
    _folder_positions: Dict[str, int] = {}

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [
            f
            for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
            and os.path.splitext(f)[1].lower() in cls._SUPPORTED_EXTENSIONS
        ]

        return {
            "required": {
                "image": (sorted(files), {"image_upload": True}),
                "use_folder": ("BOOLEAN", {"default": False}),
                "folder_path": ("STRING", {"default": ""}),
                "folder_index": (
                    "INT",
                    {"default": 0, "min": 0, "max": 10_000_000},
                ),
                "auto_increment": ("BOOLEAN", {"default": False}),
                "write_txt": ("BOOLEAN", {"default": False}),
                "txt_directory": ("STRING", {"default": ""}),
                "exiftool_path": ("STRING", {"default": ""}),
            }
        }

    def load_and_extract(
        self,
        image: str,
        use_folder: bool,
        folder_path: str,
        folder_index: int,
        auto_increment: bool,
        write_txt: bool,
        txt_directory: str,
        exiftool_path: str,
    ):
        image_path, filename, file_count, resolved_index = self._resolve_image_path(
            image, use_folder, folder_path, folder_index, auto_increment
        )

        img = self._open_image(image_path)
        output_image, output_mask = self._convert_to_tensors(img)

        raw_exif = self._read_exif_user_comment(image_path, exiftool_path)
        metadata = self._parse_user_comment(raw_exif)

        if not any(
            [
                metadata["positive_prompt"],
                metadata["negative_prompt"],
                metadata["sampler"],
                metadata["cfg"],
                metadata["seed"],
                metadata["clip_skip"],
                metadata["resources_raw"],
            ]
        ):
            print(
                "[EricCivitaiPromptExtractor] Warning: Parsed metadata is empty for "
                f"{filename}. Raw metadata length={len(raw_exif)}"
            )

        if write_txt:
            self._write_metadata_txt(
                txt_directory,
                filename,
                metadata,
                raw_exif,
                resolved_index,
                file_count,
            )

        return (
            output_image,
            output_mask,
            filename,
            image_path,
            metadata["positive_prompt"],
            metadata["negative_prompt"],
            metadata["sampler"],
            metadata["cfg"],
            metadata["seed"],
            metadata["clip_skip"],
            metadata["resources_raw"],
            raw_exif,
            file_count,
            resolved_index,
        )

    @classmethod
    def IS_CHANGED(
        cls,
        image: str,
        use_folder: bool,
        folder_path: str,
        folder_index: int,
        auto_increment: bool,
        write_txt: bool,
        txt_directory: str,
        exiftool_path: str,
    ):
        try:
            if use_folder and folder_path:
                files = cls._list_supported_files(folder_path)
                if not files:
                    return "folder-empty"

                folder_abs = os.path.abspath(folder_path)
                start_idx = min(max(folder_index, 0), len(files) - 1)
                last_idx = cls._folder_positions.get(folder_abs.lower(), start_idx - 1)
                resolved_index = (
                    (last_idx + 1) % len(files) if auto_increment else start_idx
                )
                path = os.path.join(folder_abs, files[resolved_index])
            else:
                path = folder_paths.get_annotated_filepath(image)

            m = hashlib.sha256()
            with open(path, "rb") as handle:
                m.update(handle.read())
            digest = m.hexdigest()

            return (
                f"{digest}:{path}:{folder_index}:{use_folder}:{auto_increment}:{exiftool_path}"
            )
        except Exception:
            return str(
                hash(
                    (
                        image,
                        use_folder,
                        folder_path,
                        folder_index,
                        auto_increment,
                        exiftool_path,
                    )
                )
            )

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        image: str,
        use_folder: bool,
        folder_path: str,
        folder_index: int,
        auto_increment: bool,
        write_txt: bool,
        txt_directory: str,
        exiftool_path: str,
    ):
        if use_folder:
            if not folder_path:
                return "Folder path is required when folder mode is enabled."
            if not os.path.isdir(folder_path):
                return f"Invalid folder: {folder_path}"
            files = cls._list_supported_files(folder_path)
            if not files:
                return "No supported image files found in folder."
            if not auto_increment:
                if folder_index < 0 or folder_index >= len(files):
                    return (
                        f"Folder index {folder_index} out of range (0-{len(files) - 1})."
                    )
        else:
            if not folder_paths.exists_annotated_filepath(image):
                return f"Invalid image file: {image}"

        if write_txt and txt_directory:
            try:
                os.makedirs(os.path.abspath(txt_directory), exist_ok=True)
            except Exception as exc:
                return f"Unable to create txt directory: {txt_directory} ({exc})"

        exe_candidate = cls._resolve_exiftool_executable(exiftool_path)
        if exe_candidate is None:
            return (
                "ExifTool executable not found. Provide a valid path in 'exiftool_path' "
                "or ensure it is available on the system PATH."
            )

        return True

    @classmethod
    def _list_supported_files(cls, folder_path: str) -> List[str]:
        if not folder_path:
            return []
        folder_abs = os.path.abspath(folder_path)
        try:
            entries = os.listdir(folder_abs)
        except FileNotFoundError:
            return []

        files = [
            f
            for f in entries
            if os.path.isfile(os.path.join(folder_abs, f))
            and os.path.splitext(f)[1].lower() in cls._SUPPORTED_EXTENSIONS
        ]
        return sorted(files)

    def _resolve_image_path(
        self,
        image: str,
        use_folder: bool,
        folder_path: str,
        folder_index: int,
        auto_increment: bool,
    ) -> Tuple[str, str, int, int]:
        if use_folder and folder_path:
            folder_abs = os.path.abspath(folder_path)
            files = self._list_supported_files(folder_abs)
            if not files:
                raise RuntimeError("No supported images found in folder.")

            key = folder_abs.lower()
            start_idx = min(max(folder_index, 0), len(files) - 1)

            if auto_increment:
                last_idx = self._folder_positions.get(key, start_idx - 1)
                idx = (last_idx + 1) % len(files)
            else:
                idx = start_idx

            self._folder_positions[key] = idx

            filename = files[idx]
            path = os.path.join(folder_abs, filename)
            return path, filename, len(files), idx

        path = folder_paths.get_annotated_filepath(image)
        filename = os.path.basename(path)
        return path, filename, 1 if path else 0, 0

    def _open_image(self, image_path: str) -> Image.Image:
        _, ext = os.path.splitext(image_path)
        if ext.lower() == ".svg":
            return self._load_svg(image_path)
        return node_helpers.pillow(Image.open, image_path)

    def _convert_to_tensors(self, img: Image.Image) -> Tuple[torch.Tensor, torch.Tensor]:
        output_images = []
        output_masks = []
        width = None
        height = None
        excluded_formats = {"MPO"}

        for frame in ImageSequence.Iterator(img):
            frame = node_helpers.pillow(ImageOps.exif_transpose, frame)

            if frame.mode == "I":
                frame = frame.point(lambda val: val * (1 / 255))

            rgb_frame = frame.convert("RGB")

            if width is None:
                width = rgb_frame.size[0]
                height = rgb_frame.size[1]

            if rgb_frame.size[0] != width or rgb_frame.size[1] != height:
                continue

            image_np = np.array(rgb_frame).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_np)[None,]

            if "A" in frame.getbands():
                mask_np = np.array(frame.getchannel("A")).astype(np.float32) / 255.0
                mask_tensor = 1.0 - torch.from_numpy(mask_np)
            else:
                mask_tensor = torch.zeros((64, 64), dtype=torch.float32)

            output_images.append(image_tensor)
            output_masks.append(mask_tensor.unsqueeze(0))

        if not output_images:
            raise RuntimeError("Unable to process image frames.")

        if len(output_images) > 1 and img.format not in excluded_formats:
            image_out = torch.cat(output_images, dim=0)
            mask_out = torch.cat(output_masks, dim=0)
        else:
            image_out = output_images[0]
            mask_out = output_masks[0]

        return image_out, mask_out

    @classmethod
    def _resolve_exiftool_executable(cls, exiftool_path: str) -> Optional[str]:
        candidates = []
        if exiftool_path:
            expanded = os.path.expanduser(exiftool_path)
            candidates.append(os.path.abspath(expanded))
        candidates.extend(
            [
                shutil.which(exiftool_path) if exiftool_path else None,
                shutil.which("exiftool"),
                shutil.which("exiftool.exe"),
                r"C:\\Program Files\\ExifTool\\exiftool.exe",
                r"C:\\Program Files (x86)\\ExifTool\\exiftool.exe",
                r"C:\\Program Files\\XnViewMP\\AddOn\\exiftool.exe",
            ]
        )

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _read_exif_user_comment(self, image_path: str, exiftool_path: str) -> str:
        executable = self._resolve_exiftool_executable(exiftool_path)
        if executable is None:
            print(
                "[EricCivitaiPromptExtractor] ExifTool not found. Set 'exiftool_path' input."
            )
            return ""

        commands = [
            ("usercomment", [executable, "-json", "-UserComment", image_path]),
            ("usercomment", [executable, "-s3", "-UserComment", image_path]),
            ("parameters", [executable, "-json", "-Parameters", image_path]),
            ("parameters", [executable, "-s3", "-Parameters", image_path]),
        ]

        collected: List[Tuple[str, str]] = []

        for tag_name, cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    check=False,
                )
            except FileNotFoundError:
                print(
                    "[EricCivitaiPromptExtractor] ExifTool command not found when running: "
                    f"{cmd[0]}"
                )
                return ""

            if result.returncode != 0:
                stderr = result.stderr.strip()
                if stderr:
                    print(
                        "[EricCivitaiPromptExtractor] ExifTool returned non-zero exit code: "
                        f"{stderr}"
                    )
                continue

            output = result.stdout.strip()
            if not output:
                continue

            if "-json" in cmd:
                try:
                    parsed = json.loads(output)
                    if isinstance(parsed, list) and parsed:
                        entry = parsed[0]
                        if isinstance(entry, dict):
                            for key, value in entry.items():
                                normalized = key.lower().split(":")[-1]
                                if normalized in {"usercomment", "parameters"} and isinstance(
                                    value, str
                                ):
                                    collected.append((normalized, value.strip()))
                        if not collected:
                            print(
                                "[EricCivitaiPromptExtractor] JSON output missing recognized metadata fields."
                            )
                except json.JSONDecodeError:
                    print(
                        "[EricCivitaiPromptExtractor] Failed to decode ExifTool JSON output."
                    )
            else:
                collected.append((tag_name.lower(), output))

        for source, value in collected:
            if value:
                print(
                    f"[EricCivitaiPromptExtractor] Using ExifTool {source} metadata (length={len(value)})."
                )
                return value

        return ""

    def _parse_user_comment(self, comment: str) -> dict:
        metadata = {
            "positive_prompt": "",
            "negative_prompt": "",
            "sampler": "",
            "cfg": 0.0,
            "seed": 0,
            "clip_skip": -2,
            "resources_raw": "",
        }

        if not comment:
            return metadata

        sanitized = comment.replace("\x00", "").strip()
        if not sanitized:
            return metadata

        json_metadata = self._parse_json_comment(sanitized)
        if json_metadata:
            metadata.update(json_metadata)
            return metadata

        text_metadata = self._parse_text_comment(sanitized)
        metadata.update(text_metadata)
        return metadata

    def _parse_text_comment(self, comment: str) -> dict:
        metadata = {
            "positive_prompt": "",
            "negative_prompt": "",
            "sampler": "",
            "cfg": 0.0,
            "seed": 0,
            "clip_skip": -2,
            "resources_raw": "",
        }

        cleaned_comment = re.sub(
            r"^\s*Parameters\s*[:\-]?\s*",
            "",
            comment,
            flags=re.IGNORECASE,
        )

        neg_split = re.split(
            r"Negative prompt:\s*",
            cleaned_comment,
            flags=re.IGNORECASE,
        )
        positive = neg_split[0].strip()
        remainder = neg_split[1] if len(neg_split) > 1 else ""

        steps_match = re.search(r"Steps\s*:\s*", remainder, flags=re.IGNORECASE)
        if steps_match:
            metadata["negative_prompt"] = (
                remainder[: steps_match.start()].strip().rstrip(",")
            )
            remainder = remainder[steps_match.start():]
        else:
            metadata["negative_prompt"] = remainder.strip().rstrip(",")
            remainder = ""

        metadata["positive_prompt"] = positive
        metadata["sampler"] = self._extract_field(remainder, r"Sampler")
        metadata["cfg"] = self._extract_float(remainder, r"CFG scale")
        metadata["seed"] = self._extract_int(remainder, r"Seed")
        # Clip skip: convert to negative for ComfyUI, default to -2
        clip_skip_raw = self._extract_int(remainder, r"Clip skip", default=-2)
        metadata["clip_skip"] = -abs(clip_skip_raw) if clip_skip_raw != 0 else -2
        metadata["resources_raw"] = self._extract_resources(cleaned_comment)

        return metadata

    def _parse_json_comment(self, comment: str) -> Optional[dict]:
        try:
            data = json.loads(comment)
        except json.JSONDecodeError:
            cleaned = comment.lstrip("\ufeff")
            substring_data = self._extract_json_substring(cleaned)
            if substring_data is None:
                transformed = cleaned.replace("'", '"').replace("\u0022", '"')
                try:
                    data = json.loads(transformed)
                except json.JSONDecodeError:
                    print(
                        "[EricCivitaiPromptExtractor] JSON parsing failed; falling back to text parser."
                    )
                    return None
            else:
                try:
                    data = json.loads(substring_data)
                except json.JSONDecodeError:
                    print(
                        "[EricCivitaiPromptExtractor] Failed to parse extracted JSON substring."
                    )
                    return None

        if isinstance(data, list):
            if len(data) == 1 and isinstance(data[0], dict):
                data = data[0]
            else:
                return None

        if not isinstance(data, dict):
            return None

        metadata = {
            "positive_prompt": "",
            "negative_prompt": "",
            "sampler": "",
            "cfg": 0.0,
            "seed": 0,
            "clip_skip": -2,
            "resources_raw": "",
        }

        found_any = False

        positive = self._find_prompt_in_graph(data, target_title="Positive")
        negative = self._find_prompt_in_graph(data, target_title="Negative")
        if positive:
            found_any = True
        if negative:
            found_any = True

        extra_meta = self._parse_extra_metadata(data.get("extraMetadata"))
        if extra_meta:
            if extra_meta.get("prompt"):
                positive = positive or extra_meta.get("prompt", "")
                found_any = True
            if extra_meta.get("negativePrompt"):
                negative = negative or extra_meta.get("negativePrompt", "")
                found_any = True
            metadata["sampler"] = extra_meta.get("sampler", metadata["sampler"])
            metadata["cfg"] = self._safe_float(
                extra_meta.get("cfgScale"), metadata["cfg"]
            )
            metadata["seed"] = self._safe_int(
                extra_meta.get("seed"), metadata["seed"]
            )
            clip_skip_raw = self._safe_int(
                extra_meta.get("clipSkip"), metadata["clip_skip"]
            )
            metadata["clip_skip"] = -abs(clip_skip_raw) if clip_skip_raw != 0 else -2
            found_any = True

        sampler_info = self._find_sampler_settings(data)
        if sampler_info:
            metadata["sampler"] = sampler_info.get("sampler", metadata["sampler"])
            metadata["cfg"] = sampler_info.get("cfg", metadata["cfg"])
            metadata["seed"] = sampler_info.get("seed", metadata["seed"])
            clip_skip_raw = sampler_info.get("clip_skip", metadata["clip_skip"])
            metadata["clip_skip"] = -abs(clip_skip_raw) if clip_skip_raw != 0 else -2
            found_any = True

        metadata["positive_prompt"] = positive or metadata["positive_prompt"]
        metadata["negative_prompt"] = negative or metadata["negative_prompt"]

        resources = self._collect_resources_from_graph(data)
        if extra_meta and extra_meta.get("resources"):
            for entry in extra_meta.get("resources", []):
                if isinstance(entry, dict):
                    resources.append(
                        {
                            "identifier": str(entry.get("modelVersionId")),
                            "weight": entry.get("strength"),
                            "source": "extraMetadata",
                            "type": "modelVersionId",
                        }
                    )

        if resources:
            metadata["resources_raw"] = json.dumps(resources, ensure_ascii=False)
            found_any = True

        if not found_any:
            return None

        return metadata

    def _find_prompt_in_graph(self, data: dict, target_title: str) -> str:
        for node in self._iter_dicts(data):
            if not isinstance(node, dict):
                continue
            meta = node.get("_meta", {})
            if isinstance(meta, dict) and meta.get("title", "").lower() == target_title.lower():
                inputs = node.get("inputs", {})
                if isinstance(inputs, dict):
                    text_value = inputs.get("text")
                    if isinstance(text_value, str) and text_value.strip():
                        return text_value.strip()
        return ""

    def _find_sampler_settings(self, data: dict) -> Optional[dict]:
        for node in self._iter_dicts(data):
            if not isinstance(node, dict):
                continue
            class_type = node.get("class_type", "").lower()
            if class_type in {"ksampler", "ksampleradvanced"}:
                inputs = node.get("inputs", {})
                if not isinstance(inputs, dict):
                    continue
                return {
                    "sampler": inputs.get("sampler_name") or inputs.get("sampler", ""),
                    "cfg": self._safe_float(inputs.get("cfg"), 0.0),
                    "seed": self._safe_int(inputs.get("seed"), 0),
                    "clip_skip": self._safe_int(
                        inputs.get("clip_skip", inputs.get("clip")), 0
                    ),
                }
        return None

    def _collect_resources_from_graph(self, data: dict) -> List[dict]:
        resources: List[dict] = []

        for node_key, node_val in data.items():
            if not isinstance(node_val, dict):
                continue
            inputs = node_val.get("inputs", {})
            if not isinstance(inputs, dict):
                continue
            for key, value in inputs.items():
                if isinstance(value, str) and value.startswith("urn:air:"):
                    weight = inputs.get("strength_model")
                    if weight is None:
                        weight = inputs.get("strength_clip")
                    resources.append(
                        {
                            "identifier": value,
                            "type": key,
                            "source": node_key,
                            "weight": weight,
                        }
                    )

        extra = data.get("extra")
        if isinstance(extra, dict):
            airs = extra.get("airs")
            if isinstance(airs, list):
                for value in airs:
                    if isinstance(value, str):
                        resources.append(
                            {
                                "identifier": value,
                                "type": "urn",
                                "source": "extra.airs",
                                "weight": None,
                            }
                        )

        return resources

    def _parse_extra_metadata(self, extra_metadata: Optional[str]) -> Optional[dict]:
        if not extra_metadata or not isinstance(extra_metadata, str):
            return None
        try:
            return json.loads(extra_metadata)
        except json.JSONDecodeError:
            return None

    def _iter_dicts(self, data):
        if isinstance(data, dict):
            yield data
            for value in data.values():
                yield from self._iter_dicts(value)
        elif isinstance(data, list):
            for item in data:
                yield from self._iter_dicts(item)

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _extract_json_substring(text: str) -> Optional[str]:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = text[start : end + 1]
        balance = 0
        for idx, char in enumerate(candidate):
            if char == "{":
                balance += 1
            elif char == "}":
                balance -= 1
                if balance == 0 and idx != len(candidate) - 1:
                    trimmed = candidate[: idx + 1]
                    try:
                        json.loads(trimmed)
                        return trimmed
                    except json.JSONDecodeError:
                        continue
        return candidate

    @staticmethod
    def _extract_field(text: str, label: str) -> str:
        pattern = re.compile(rf"{label}\s*:\s*([^,\n]+)", flags=re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return ""
        return match.group(1).strip()

    @staticmethod
    def _extract_int(text: str, label: str, default: int = 0) -> int:
        pattern = re.compile(rf"{label}\s*:\s*([-+]?[0-9]+)", flags=re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return default
        try:
            return int(match.group(1))
        except ValueError:
            return default

    @staticmethod
    def _extract_float(text: str, label: str) -> float:
        pattern = re.compile(
            rf"{label}\s*:\s*([0-9]+\.?[0-9]*)",
            flags=re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            return 0.0
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0

    @staticmethod
    def _extract_resources(text: str) -> str:
        pattern = re.compile(
            r"Civitai resources\s*:\s*(\[[\s\S]*?\])\s*(?:Civitai metadata|$)",
            flags=re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            return ""
        return match.group(1).strip()

    def _write_metadata_txt(
        self,
        txt_directory: str,
        filename: str,
        metadata: dict,
        raw_exif: str,
        resolved_index: int,
        file_count: int,
    ):
        if not txt_directory:
            return

        out_dir = os.path.abspath(txt_directory)
        os.makedirs(out_dir, exist_ok=True)
        txt_path = os.path.join(out_dir, f"{os.path.splitext(filename)[0]}.txt")

        resources_summary = self._format_resources(metadata["resources_raw"])

        lines = [
            "**Positive Prompt**",
            metadata["positive_prompt"] or "(missing)",
            "",
            "**Negative Prompt**",
            metadata["negative_prompt"] or "(missing)",
            "",
            "**Sampler**",
            metadata["sampler"] or "(missing)",
            "",
            "**CFG Scale**",
            str(metadata["cfg"]),
            "",
            "**Seed**",
            str(metadata["seed"]),
            "",
            "**Clip Skip**",
            str(metadata["clip_skip"]),
            "",
            "**Resources**",
            resources_summary or "(missing)",
            "",
            "**Raw Metadata**",
            raw_exif or "(missing)",
            "",
            "**Folder Context**",
            f"Index {resolved_index} of {file_count}",
        ]

        with open(txt_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    @staticmethod
    def _format_resources(resources_raw: str) -> str:
        if not resources_raw:
            return ""

        try:
            parsed = json.loads(resources_raw)
        except json.JSONDecodeError:
            return resources_raw

        if not isinstance(parsed, list):
            return resources_raw

        lines = []
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            identifier = entry.get("identifier") or entry.get("modelVersionId")
            resource_type = entry.get("type", "resource")
            model_name = entry.get("modelName", "")
            version_name = entry.get("modelVersionName", "")
            weight = entry.get("weight")
            source = entry.get("source")

            parts = []
            if resource_type:
                parts.append(str(resource_type))
            if identifier:
                parts.append(str(identifier))
            elif model_name:
                parts.append(model_name)
            if version_name:
                parts.append(f"({version_name})")

            line = " ".join(part for part in parts if part)
            annotations = []
            if weight is not None:
                annotations.append(f"weight={weight}")
            if source:
                annotations.append(f"source={source}")
            if annotations:
                line += f" [{', '.join(annotations)}]"

            if line:
                lines.append(f"- {line}")

        return "\n".join(lines) if lines else resources_raw

    @staticmethod
    def decode_resources(resources_raw: str) -> List[Dict[str, Any]]:
        """Return structured Civitai resource entries extracted from metadata."""

        if not resources_raw:
            return []

        try:
            parsed = json.loads(resources_raw)
        except json.JSONDecodeError:
            return []

        if isinstance(parsed, dict):
            parsed = [parsed]

        resources: List[Dict[str, Any]] = []
        for entry in parsed:
            if isinstance(entry, dict):
                resources.append(entry)
        return resources

    def _load_svg(self, svg_path: str, width: int = 1024, height: int = 1024) -> Image.Image:
        try:
            import cairosvg
            from io import BytesIO

            png_data = cairosvg.svg2png(
                url=svg_path,
                output_width=width,
                output_height=height,
            )
            img = Image.open(BytesIO(png_data))
            return img
        except ImportError:
            try:
                from io import BytesIO

                from reportlab.graphics import renderPM
                from svglib.svglib import svg2rlg

                drawing = svg2rlg(svg_path)
                png_data = BytesIO()
                renderPM.drawToFile(drawing, png_data, fmt="PNG")
                png_data.seek(0)
                img = Image.open(png_data)
                return img
            except ImportError:
                return Image.new("RGB", (width, height), color=(128, 128, 128))

class _CivitaiAPIClient:
    """Simple helper that caches Civitai API responses on disk."""

    _BASE_URL = "https://civitai.com/api/v1/model-versions/{version_id}"

    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if not self.cache_path:
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print(
                "[EricCivitaiAutoLoader] Failed to parse Civitai cache; starting fresh."
            )
            return {}

        return data if isinstance(data, dict) else {}

    def _save_cache(self):
        if not self.cache_path:
            return
        try:
            with open(self.cache_path, "w", encoding="utf-8") as handle:
                json.dump(self._cache, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            print(f"[EricCivitaiAutoLoader] Unable to write cache file: {exc}")

    def get_model_version(self, version_id: int) -> Optional[Dict[str, Any]]:
        key = str(version_id)
        if key in self._cache:
            return self._cache[key]

        url = self._BASE_URL.format(version_id=version_id)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(
                    f"[EricCivitaiAutoLoader] Civitai API returned {response.status_code} for {url}"
                )
                return None
            data = response.json()
        except requests.RequestException as exc:
            print(f"[EricCivitaiAutoLoader] Civitai API request failed: {exc}")
            return None
        except json.JSONDecodeError:
            print("[EricCivitaiAutoLoader] Invalid JSON received from Civitai API.")
            return None

        if isinstance(data, dict):
            self._cache[key] = data
            self._save_cache()
            return data
        return None


class EricCivitaiPromptExtractorAutoLoader(EricCivitaiPromptExtractor):
    """Extend the extractor with automatic Civitai LoRA discovery and loading."""

    CATEGORY = EricCivitaiPromptExtractor.CATEGORY
    FUNCTION = "load_extract_and_apply"
    RETURN_TYPES = (
        "MODEL",
        "CLIP",
    ) + EricCivitaiPromptExtractor.RETURN_TYPES + ("STRING",)
    RETURN_NAMES = (
        "model",
        "clip",
    ) + EricCivitaiPromptExtractor.RETURN_NAMES + ("status",)

    def __init__(self):
        super().__init__()
        base_dir = os.path.dirname(__file__)
        cache_path = os.path.join(base_dir, "civitai_cache.json")
        self._civitai_client = _CivitaiAPIClient(cache_path)
        self._local_lora_index: Optional[Dict[str, List[str]]] = None
        self._sanitized_lora_index: Optional[Dict[str, List[str]]] = None

    @classmethod
    def INPUT_TYPES(cls):
        base_inputs = EricCivitaiPromptExtractor.INPUT_TYPES()
        base_required = dict(base_inputs.get("required", {}))

        required = {
            "model": ("MODEL",),
            "clip": ("CLIP",),
        }
        required.update(base_required)

        optional = {
            "max_loras": ("INT", {"default": 4, "min": 0, "max": 16}),
            "use_primary_only": ("BOOLEAN", {"default": True}),
            "use_resource_weights": ("BOOLEAN", {"default": True}),
            "default_strength": (
                "FLOAT",
                {"default": 0.75, "min": 0.0, "max": 5.0, "step": 0.05},
            ),
            "default_clip_strength": (
                "FLOAT",
                {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05},
            ),
            "query_civitai": ("BOOLEAN", {"default": True}),
            "refresh_lora_index": ("BOOLEAN", {"default": False}),
        }

        return {"required": required, "optional": optional}

    def load_extract_and_apply(
        self,
        model,
        clip,
        image,
        use_folder,
        folder_path,
        folder_index,
        auto_increment,
        write_txt,
        txt_directory,
        exiftool_path,
        max_loras=4,
        use_primary_only=True,
        use_resource_weights=True,
        default_strength=0.75,
        default_clip_strength=1.0,
        query_civitai=True,
        refresh_lora_index=False,
    ):
        extractor_outputs = super().load_and_extract(
            image,
            use_folder,
            folder_path,
            folder_index,
            auto_increment,
            write_txt,
            txt_directory,
            exiftool_path,
        )

        (
            image_tensor,
            mask,
            filename,
            full_path,
            positive_prompt,
            negative_prompt,
            sampler,
            cfg,
            seed,
            clip_skip,
            resources_raw,
            raw_exif,
            file_count,
            current_index,
        ) = extractor_outputs

        updated_model, updated_clip, status_lines = self._apply_loras_from_metadata(
            model,
            clip,
            resources_raw,
            max_loras=max_loras,
            use_primary_only=use_primary_only,
            use_resource_weights=use_resource_weights,
            default_strength=default_strength,
            default_clip_strength=default_clip_strength,
            query_civitai=query_civitai,
            refresh_index=refresh_lora_index,
            positive_prompt=positive_prompt,
            raw_exif=raw_exif,
        )

        status = "\n".join(status_lines) if status_lines else "No matching Civitai LoRAs found."

        return (
            updated_model,
            updated_clip,
            image_tensor,
            mask,
            filename,
            full_path,
            positive_prompt,
            negative_prompt,
            sampler,
            cfg,
            seed,
            clip_skip,
            resources_raw,
            raw_exif,
            file_count,
            current_index,
            status,
        )

    def _apply_loras_from_metadata(
        self,
        model,
        clip,
        resources_raw: str,
        *,
        max_loras: int,
        use_primary_only: bool,
        use_resource_weights: bool,
        default_strength: float,
        default_clip_strength: float,
        query_civitai: bool,
        refresh_index: bool,
        positive_prompt: str = "",
        raw_exif: str = "",
    ) -> Tuple[Any, Any, List[str]]:
        resources = self.decode_resources(resources_raw)
        
        # Parse A1111-style LoRA tags from prompt and raw EXIF
        a1111_loras = []
        if positive_prompt:
            a1111_loras.extend(self._parse_a1111_lora_tags(positive_prompt))
        if raw_exif:
            a1111_loras.extend(self._parse_a1111_lora_tags(raw_exif))
        
        # Remove duplicates while preserving order
        seen_names = set()
        unique_a1111_loras = []
        for lora in a1111_loras:
            name_lower = lora['name'].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_a1111_loras.append(lora)
        
        if not resources and not unique_a1111_loras:
            return model, clip, ["No Civitai resources or A1111 LoRA tags found in metadata."]

        model_current = model
        clip_current = clip
        status: List[str] = []
        loaded = 0
        
        # Debug info
        if resources:
            lora_types = [str(r.get("type") or r.get("modelType", "unknown")) for r in resources]
            status.append(f"Found {len(resources)} Civitai resources: {', '.join(set(lora_types))}")
        if unique_a1111_loras:
            status.append(f"Found {len(unique_a1111_loras)} A1111 LoRA tags in prompt/EXIF")

        self._ensure_local_index(refresh=refresh_index)

        # First, process Civitai resources from JSON metadata
        for entry in resources:
            if max_loras > 0 and loaded >= max_loras:
                break

            # Check both 'type' and 'modelType' fields (Civitai uses both)
            model_type = str(entry.get("type") or entry.get("modelType", "")).lower()
            # Accept lora, lycoris (LyCORIS), and locon (LoHA/LoKr) types
            if model_type not in ("lora", "lycoris", "locon"):
                continue
            if use_primary_only and not entry.get("isPrimary", False):
                continue

            version_id = self._coerce_int(entry.get("modelVersionId"))
            if version_id is None:
                status.append("Skipped resource missing modelVersionId.")
                continue

            civitai_info = None
            if query_civitai:
                civitai_info = self._civitai_client.get_model_version(version_id)
                if civitai_info is None:
                    status.append(
                        f"Civitai lookup failed for modelVersionId {version_id}."
                    )

            candidates = self._collect_candidate_filenames(entry, civitai_info)

            lora_path = self._find_local_lora(candidates, entry)
            
            # If not found by filename, try to find by version ID in filename
            if not lora_path and version_id:
                lora_path = self._find_lora_by_version_id(version_id)
                if lora_path:
                    status.append(f"Found LoRA by version ID {version_id}: {os.path.basename(lora_path)}")
            
            if not lora_path:
                model_name = entry.get("modelName") or f"version {version_id}"
                status.append(f"{model_type.upper()} '{model_name}' (ID: {version_id}) not found in local directories.")
                continue

            strength = default_strength
            if use_resource_weights:
                strength = self._safe_float(entry.get("weight"), default_strength)

            clip_strength = (
                default_clip_strength if default_clip_strength is not None else strength
            )

            try:
                lora_state = comfy.utils.load_torch_file(lora_path, safe_load=True)
                model_current, clip_current = comfy.sd.load_lora_for_models(
                    model_current,
                    clip_current,
                    lora_state,
                    strength,
                    clip_strength,
                )
                status.append(
                    f"Loaded {model_type.upper()}: {os.path.basename(lora_path)} "
                    f"(strength={strength:.2f}, clip={clip_strength:.2f})"
                )
                loaded += 1
            except Exception as exc:
                status.append(f"Failed to load {model_type.upper()} {os.path.basename(lora_path)}: {exc}")

        # Second, process A1111-style LoRA tags from prompt/EXIF
        for lora_info in unique_a1111_loras:
            if max_loras > 0 and loaded >= max_loras:
                status.append(f"Max LoRAs ({max_loras}) reached; skipping remaining A1111 tags.")
                break
            
            lora_name = lora_info['name']
            weight = lora_info['weight']
            
            lora_path = None
            
            # First, try to find by name in the tag
            candidates = self._generate_a1111_candidates(lora_name)
            lora_path = self._find_local_lora_by_candidates(candidates)
            
            # If not found and name looks like it could reference a resource, check Civitai resources
            if not lora_path and resources:
                # Check if lora_name matches any model names or version IDs in resources
                for resource in resources:
                    # Check both 'type' and 'modelType' fields
                    resource_type = str(resource.get("type") or resource.get("modelType", "")).lower()
                    # Accept lora, lycoris, and locon types
                    if resource_type not in ("lora", "lycoris", "locon"):
                        continue
                    
                    # Check by model name match
                    model_name = resource.get("modelName", "")
                    if model_name and self._sanitize_token(model_name) == self._sanitize_token(lora_name):
                        # Found a matching resource, try to find it
                        version_id = self._coerce_int(resource.get("modelVersionId"))
                        if version_id:
                            temp_path = self._find_lora_by_version_id(version_id)
                            if temp_path:
                                lora_path = temp_path
                                status.append(f"A1111 tag '{lora_name}' matched Civitai resource (ID: {version_id})")
                                break
            
            if not lora_path:
                status.append(f"A1111 LoRA '{lora_name}' not found in local directories.")
                continue
            
            # Use the weight from the tag if use_resource_weights is enabled
            strength = weight if use_resource_weights else default_strength
            clip_strength = (
                default_clip_strength if default_clip_strength is not None else strength
            )
            
            try:
                lora_state = comfy.utils.load_torch_file(lora_path, safe_load=True)
                model_current, clip_current = comfy.sd.load_lora_for_models(
                    model_current,
                    clip_current,
                    lora_state,
                    strength,
                    clip_strength,
                )
                status.append(
                    f"Loaded A1111 tag: {os.path.basename(lora_path)} "
                    f"(strength={strength:.2f}, clip={clip_strength:.2f})"
                )
                loaded += 1
            except Exception as exc:
                status.append(f"Failed to load A1111 LoRA {os.path.basename(lora_path)}: {exc}")

        if loaded == 0 and not status:
            status.append("No matching Civitai LoRA resources or A1111 tags found.")

        return model_current, clip_current, status

    def _ensure_local_index(self, refresh: bool = False):
        if (
            not refresh
            and self._local_lora_index is not None
            and self._sanitized_lora_index is not None
        ):
            return

        index: Dict[str, List[str]] = {}
        sanitized_index: Dict[str, List[str]] = {}
        
        # Collect all LoRA-type model directories (includes loras, lycoris, etc.)
        search_dirs = []
        for folder_type in ["loras", "lycoris"]:
            try:
                dirs = folder_paths.get_folder_paths(folder_type)
                search_dirs.extend(dirs)
            except:
                # Folder type might not exist in this ComfyUI setup
                pass
        
        for base_dir in search_dirs:
            if not os.path.isdir(base_dir):
                continue
            for root, _, files in os.walk(base_dir):
                for filename in files:
                    lower = filename.lower()
                    path = os.path.join(root, filename)
                    index.setdefault(lower, []).append(path)
                    sanitized_key = self._sanitize_token(os.path.splitext(filename)[0])
                    if sanitized_key:
                        sanitized_index.setdefault(sanitized_key, []).append(path)

        self._local_lora_index = index
        self._sanitized_lora_index = sanitized_index

    def _collect_candidate_filenames(
        self, entry: Dict[str, Any], civitai_info: Optional[Dict[str, Any]]
    ) -> List[str]:
        candidates: List[str] = []

        def add_candidate(value: Optional[str]):
            if not value:
                return
            name = os.path.basename(value)
            if name and name not in candidates:
                candidates.append(name)

        add_candidate(entry.get("fileName"))
        add_candidate(entry.get("filename"))

        files = civitai_info.get("files") if isinstance(civitai_info, dict) else None
        if isinstance(files, list):
            for file_info in files:
                if not isinstance(file_info, dict):
                    continue
                add_candidate(file_info.get("name"))
                download_url = file_info.get("downloadUrl" )
                if isinstance(download_url, str) and download_url:
                    add_candidate(download_url.split("/")[-1])

        model_name = entry.get("modelName")
        version_name = entry.get("modelVersionName")
        if isinstance(model_name, str):
            sanitized_version = ""
            if isinstance(version_name, str):
                sanitized_version = version_name.replace(" ", "_")
            for ext in (".safetensors", ".pt", ".ckpt"):
                add_candidate(f"{model_name}{ext}")
                if sanitized_version:
                    add_candidate(f"{model_name}-{sanitized_version}{ext}")
                    add_candidate(f"{model_name}_{sanitized_version}{ext}")

        return candidates

    def _find_local_lora(
        self, candidate_names: List[str], entry: Dict[str, Any]
    ) -> Optional[str]:
        if self._local_lora_index is None or self._sanitized_lora_index is None:
            self._ensure_local_index()

        for candidate in candidate_names:
            lower = candidate.lower()
            matches = self._local_lora_index.get(lower)
            if matches:
                return matches[0]

        for candidate in candidate_names:
            sanitized = self._sanitize_token(os.path.splitext(candidate)[0])
            if not sanitized:
                continue
            matches = self._sanitized_lora_index.get(sanitized)
            if matches:
                return matches[0]

        model_name = entry.get("modelName")
        if isinstance(model_name, str):
            sanitized = self._sanitize_token(model_name)
            matches = self._sanitized_lora_index.get(sanitized)
            if matches:
                return matches[0]

        return None

    def _generate_a1111_candidates(self, lora_name: str) -> List[str]:
        """
        Generate candidate filenames for A1111-style LoRA names.
        Handles names with spaces, special characters, and extensions.
        """
        candidates = []
        
        # Common extensions
        extensions = [".safetensors", ".pt", ".ckpt"]
        
        # Add exact name with extensions
        for ext in extensions:
            candidates.append(f"{lora_name}{ext}")
        
        # Add with underscores instead of spaces
        name_underscore = lora_name.replace(" ", "_")
        if name_underscore != lora_name:
            for ext in extensions:
                candidates.append(f"{name_underscore}{ext}")
        
        # Add with no spaces
        name_nospace = lora_name.replace(" ", "")
        if name_nospace != lora_name and name_nospace != name_underscore:
            for ext in extensions:
                candidates.append(f"{name_nospace}{ext}")
        
        # Add lowercase variations
        name_lower = lora_name.lower()
        if name_lower != lora_name:
            for ext in extensions:
                candidates.append(f"{name_lower}{ext}")
        
        return candidates

    def _find_local_lora_by_candidates(self, candidate_names: List[str]) -> Optional[str]:
        """
        Find a local LoRA file by checking candidate names.
        Similar to _find_local_lora but without entry parameter.
        """
        if self._local_lora_index is None or self._sanitized_lora_index is None:
            self._ensure_local_index()

        # First pass: exact filename match (case-insensitive)
        for candidate in candidate_names:
            lower = candidate.lower()
            matches = self._local_lora_index.get(lower)
            if matches:
                return matches[0]

        # Second pass: sanitized match
        for candidate in candidate_names:
            sanitized = self._sanitize_token(os.path.splitext(candidate)[0])
            if not sanitized:
                continue
            matches = self._sanitized_lora_index.get(sanitized)
            if matches:
                return matches[0]

        # Third pass: partial filename match (contains the candidate name)
        for candidate in candidate_names:
            candidate_lower = os.path.splitext(candidate)[0].lower()
            sanitized_candidate = self._sanitize_token(candidate_lower)
            
            for filename_lower, paths in self._local_lora_index.items():
                filename_base = os.path.splitext(filename_lower)[0]
                
                # Check if candidate is contained in filename
                if candidate_lower in filename_base:
                    return paths[0]
                
                # Check sanitized versions
                if sanitized_candidate and sanitized_candidate in self._sanitize_token(filename_base):
                    return paths[0]

        return None

    @staticmethod
    def _sanitize_token(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _find_lora_by_version_id(self, version_id: int) -> Optional[str]:
        """
        Try to find a local LoRA file that contains the model version ID in its filename.
        Format: {version_id}_*.safetensors or similar
        """
        if self._local_lora_index is None:
            self._ensure_local_index()
        
        version_str = str(version_id)
        
        # Check all indexed files for version ID in filename
        for filename_lower, paths in self._local_lora_index.items():
            filename_base = os.path.splitext(filename_lower)[0]
            # Check if version ID appears at start or after underscore
            if filename_base.startswith(version_str + "_") or \
               filename_base.startswith(version_str + "-") or \
               f"_{version_str}_" in filename_base or \
               f"_{version_str}-" in filename_base:
                return paths[0]
        
        return None

    @staticmethod
    def _parse_a1111_lora_tags(text: str) -> List[Dict[str, Any]]:
        """
        Parse A1111-style LoRA tags from text.
        Format: <lora:name:weight> or <lora:name>
        Returns list of dicts with 'name' and 'weight' keys.
        """
        if not text:
            return []
        
        # Match <lora:name:weight> or <lora:name>
        pattern = r'<lora:([^:>]+)(?::([-+]?\d*\.?\d+))?>'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        loras = []
        for name, weight_str in matches:
            name = name.strip()
            if not name:
                continue
            
            # Parse weight, default to 1.0 if not specified
            weight = 1.0
            if weight_str:
                try:
                    weight = float(weight_str)
                except ValueError:
                    weight = 1.0
            
            loras.append({
                'name': name,
                'weight': weight,
                'source': 'a1111_tag'
            })
        
        return loras


NODE_CLASS_MAPPINGS = {
    "EricCivitaiPromptExtractor": EricCivitaiPromptExtractor,
    "EricCivitaiPromptExtractorAutoLoader": EricCivitaiPromptExtractorAutoLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricCivitaiPromptExtractor": "Eric Civitai Prompt Extractor",
    "EricCivitaiPromptExtractorAutoLoader": "Eric Civitai Prompt Extractor + Auto LoRA Loader",
}
