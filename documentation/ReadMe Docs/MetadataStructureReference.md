# Metadata Structure Reference

This document provides a comprehensive reference for the metadata structure used in the Metadata System for ComfyUI. It details the fields, their meanings, and their organization.

## Overview

The metadata is organized into a structured hierarchy with four main sections:

- **basic**: Essential information such as title, description, and keywords
- **analysis**: Image analysis results including technical and aesthetic measures
- **ai_info**: AI generation information including model, prompt, and workflow data
- **regions**: Information about specific regions in the image (faces, objects)

## Basic Section

The `basic` section contains essential information about the image:

```json
"basic": {
    "title": "Mountain Landscape",
    "description": "AI generated mountain landscape with snow and trees",
    "keywords": ["mountains", "landscape", "snow", "trees", "AI generated"],
    "rating": 4,
    "creator": "John Doe",
    "rights": "Copyright © 2025 John Doe",
    "create_date": "2025-03-15T12:34:56"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `title` | String | The title or name of the image |
| `description` | String | Detailed description or caption for the image |
| `keywords` | Array | Tags or keywords that describe the image content |
| `rating` | Integer | User-assigned rating (1-5 stars) |
| `creator` | String | Name of the image creator or photographer |
| `rights` | String | Copyright or licensing information |
| `create_date` | String | Creation date in ISO 8601 format |

## Analysis Section

The `analysis` section contains image analysis results:

```json
"analysis": {
    "technical": {
        "blur": {
            "score": 0.92,
            "higher_better": true,
            "timestamp": "2025-03-15T12:34:56"
        },
        "noise": {
            "score": 0.08,
            "higher_better": false,
            "timestamp": "2025-03-15T12:34:56"
        },
        "dimensions": {
            "width": 512,
            "height": 512,
            "ratio": 1.0
        },
        "artifacts": {
            "detected": false,
            "score": 0.03
        }
    },
    "aesthetic": {
        "composition": 7.8,
        "color_harmony": 8.2,
        "overall": 7.9,
        "timestamp": "2025-03-15T12:34:56"
    },
    "pyiqa": {
        "niqe": {
            "score": 3.45,
            "higher_better": false,
            "range": [0, 25],
            "timestamp": "2025-03-15T12:34:56"
        },
        "musiq": {
            "score": 78.2,
            "higher_better": true,
            "range": [0, 100],
            "timestamp": "2025-03-15T12:34:56"
        },
        "clipiqa": {
            "score": 0.82,
            "higher_better": true,
            "range": [0, 1],
            "timestamp": "2025-03-15T12:34:56"
        }
    },
    "classification": {
        "style": {
            "value": "photorealistic",
            "confidence": 0.87,
            "timestamp": "2025-03-15T12:34:56"
        },
        "content_type": {
            "value": "landscape",
            "confidence": 0.94,
            "timestamp": "2025-03-15T12:34:56"
        },
        "has_text": {
            "value": false,
            "confidence": 0.98,
            "timestamp": "2025-03-15T12:34:56"
        }
    },
    "eiqa": {
        "color": {
            "dominant_colors": [
                {
                    "name": "forest_green",
                    "hex": "#228B22",
                    "percentage": 0.35
                },
                {
                    "name": "snow",
                    "hex": "#FFFAFA",
                    "percentage": 0.28
                },
                {
                    "name": "sky_blue",
                    "hex": "#87CEEB",
                    "percentage": 0.25
                }
            ],
            "harmony": {
                "type": "complementary",
                "score": 0.85,
                "is_harmonious": true
            },
            "characteristics": {
                "temperature": "cool",
                "contrast": "high",
                "saturation": "medium"
            }
        }
    }
}
```

### Technical Subsection

| Field | Type | Description |
|-------|------|-------------|
| `blur` | Object | Blur detection metrics |
| `blur.score` | Number | Blur score (higher values mean sharper for most detectors) |
| `blur.higher_better` | Boolean | Whether higher score means better quality |
| `noise` | Object | Noise detection metrics |
| `noise.score` | Number | Noise score (lower usually better) |
| `noise.higher_better` | Boolean | Whether higher score means better quality |
| `dimensions` | Object | Image dimension information |
| `dimensions.width` | Integer | Image width in pixels |
| `dimensions.height` | Integer | Image height in pixels |
| `dimensions.ratio` | Number | Aspect ratio (width/height) |

### Aesthetic Subsection

| Field | Type | Description |
|-------|------|-------------|
| `composition` | Number | Composition quality score (0-10) |
| `color_harmony` | Number | Color harmony score (0-10) |
| `overall` | Number | Overall aesthetic score (0-10) |

### PyIQA Subsection

Contains scores from various Image Quality Assessment (IQA) models:

| Field | Type | Description |
|-------|------|-------------|
| `niqe` | Object | Natural Image Quality Evaluator scores |
| `musiq` | Object | Multi-scale Image Quality Transformer scores |
| `clipiqa` | Object | CLIP-based Image Quality Assessment scores |

Each IQA model entry includes:
- `score`: The quality score
- `higher_better`: Whether higher scores mean better quality
- `range`: The score range as [min, max]
- `timestamp`: When the analysis was performed

### Classification Subsection

| Field | Type | Description |
|-------|------|-------------|
| `style` | Object | Detected image style information |
| `content_type` | Object | Detected content type |
| `has_text` | Object | Text detection results |

Classification entries include:
- `value`: The detected classification
- `confidence`: Confidence score (0-1)
- `timestamp`: When the classification was performed

### EIQA Color Subsection

| Field | Type | Description |
|-------|------|-------------|
| `dominant_colors` | Array | List of dominant colors in the image |
| `harmony` | Object | Color harmony analysis |
| `characteristics` | Object | General color characteristics |

## AI Info Section

The `ai_info` section contains information about AI generation:

```json
"ai_info": {
    "generation": {
        "model": "stable-diffusion-v1-5",
        "prompt": "majestic mountains with snow caps, trees in foreground, clear blue sky",
        "negative_prompt": "ugly, blurry, low quality, deformed",
        "sampler": "euler_a",
        "steps": 30,
        "cfg_scale": 7.5,
        "seed": 1234567890,
        "width": 512,
        "height": 512,
        "batch_size": 1,
        "loras": [
            {
                "name": "landscape_lora",
                "strength": 0.8
            }
        ],
        "timestamp": "2025-03-15T12:34:56"
    },
    "workflow": {
        "nodes": {
            "1": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 1234567890,
                    "steps": 30,
                    "cfg": 7.5,
                    "sampler_name": "euler_a",
                    "scheduler": "normal",
                    "denoise": 1.0
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "majestic mountains with snow caps, trees in foreground, clear blue sky"
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "ugly, blurry, low quality, deformed"
                },
                "is_negative": true
            }
            // More nodes...
        }
    }
}
```

### Generation Subsection

| Field | Type | Description |
|-------|------|-------------|
| `model` | String | Base model name/identifier |
| `prompt` | String | Main generation prompt |
| `negative_prompt` | String | Negative prompt for undesired elements |
| `sampler` | String | Sampling algorithm used |
| `steps` | Integer | Number of sampling steps |
| `cfg_scale` | Number | Classifier-free guidance scale |
| `seed` | Number | Generation seed value |
| `width` | Integer | Generated image width |
| `height` | Integer | Generated image height |
| `loras` | Array | LoRA models used in generation |

### Workflow Subsection

Contains the complete ComfyUI workflow data, including:
- Node definitions and connections
- Model parameters and settings
- Processing pipeline structure

This preserves the entire generation process for reproducibility.

## Regions Section

The `regions` section contains information about specific regions in the image:

```json
"regions": {
    "faces": [
        {
            "type": "Face",
            "name": "Person 1",
            "area": {
                "x": 0.2,
                "y": 0.3,
                "w": 0.1,
                "h": 0.15
            },
            "extensions": {
                "eiqa": {
                    "face_analysis": {
                        "gender": "female",
                        "age": 28,
                        "emotion": "happy",
                        "scores": {
                            "confidence": 0.94,
                            "quality": 0.87
                        }
                    }
                }
            }
        }
    ],
    "areas": [
        {
            "type": "Object",
            "name": "Mountain",
            "area": {
                "x": 0.1,
                "y": 0.2,
                "w": 0.8,
                "h": 0.5
            }
        }
    ],
    "summary": {
        "face_count": 1,
        "detector_type": "deepface"
    }
}
```

### Faces Subsection

Contains detected faces with:
- `type`: Face region type
- `name`: Face identifier/name
- `area`: Position and size (normalized 0-1 coordinates)
- `extensions`: Additional analysis data

### Areas Subsection

Contains other detected regions with:
- `type`: Area/object type
- `name`: Area identifier/name
- `area`: Position and size (normalized 0-1 coordinates)

### Summary Subsection

Contains summary statistics about detected regions.

## Additional Metadata Formats

### XMP Format

The metadata system complies with XMP (Extensible Metadata Platform) standards:

- **Dublin Core (dc) Namespace**: For basic properties (title, description)
- **XMP Basic (xmp) Namespace**: For general properties (rating, dates)
- **MWG Regions (mwg-rs) Namespace**: For face/area information
- **Custom Namespaces**: For AI and analysis data

### Exif Format

Embeds metadata in EXIF headers for formats that support it:
- Title → Exif.Image.ImageDescription
- Description → Exif.Photo.UserComment
- Rating → Exif.Image.Rating

### IPTC Format

Uses IPTC fields for maximum compatibility:
- Title → Iptc.Application2.ObjectName
- Description → Iptc.Application2.Caption
- Keywords → Iptc.Application2.Keywords

## Storage Strategy

The system uses a multi-target storage approach:

1. **Embedded Metadata**: Directly inside image files where supported
2. **XMP Sidecar Files**: Standard `.xmp` files alongside images
3. **Text Files**: Both machine-readable and human-readable formats
4. **Database Storage**: Structured SQLite database for advanced queries

This ensures maximum compatibility and accessibility across different workflows and applications.

## Schema Evolution

The metadata schema is designed for easy extension:

- **New Analysis Types**: Can be added under the `analysis` section
- **New AI Models**: Supported through the flexible `generation` structure
- **Custom Fields**: Can be added at any level without breaking compatibility