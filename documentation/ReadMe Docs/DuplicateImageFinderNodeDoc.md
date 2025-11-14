# Image Duplicate Finder Node Documentation

## Overview

The Image Duplicate Finder is an advanced node for ComfyUI that scans folders of images to identify duplicates and similar images using perceptual hashing algorithms. It offers extensive options for detecting, analyzing, and managing duplicate images with multi-level similarity detection.

## Key Features

- **Multiple Hash Algorithm Support**: Choose from different perceptual hashing methods (phash, dhash, average_hash, whash-haar) to identify duplicates
- **Multi-level Similarity Detection**: Identify exact duplicates, similar images, and variants with configurable thresholds
- **Filename and Metadata Analysis**: Enhance detection by analyzing filenames and metadata
- **Metadata Integration**: Store and retrieve hash data using the metadata system
- **Duplicate Management**: Options for moving, copying, or organizing duplicate files
- **Comprehensive Reporting**: Detailed statistics and reports in both JSON and CSV formats

## Input Parameters

### Required Inputs

- **folder_path**: Primary directory to scan for duplicate images
- **primary_hash**: Algorithm to use for image comparison:
  - **phash**: Perceptual hash (best general-purpose algorithm)
  - **average_hash**: Simple but fast algorithm
  - **dhash**: Difference hash (good for detecting gradients)
  - **whash-haar**: Wavelet hash using Haar wavelets
- **exact_duplicate_threshold**: Similarity threshold for exact duplicates (0.5-1.0)
- **similar_image_threshold**: Similarity threshold for similar images (0.3-1.0)
- **variant_threshold**: Similarity threshold for variant detection (0.3-1.0)

### Optional Inputs

#### Scanning Options
- **recursive**: Scan subdirectories of the main folder
- **additional_folders**: Additional directories to scan (one path per line)
- **secondary_hash**: Optional second algorithm for improved accuracy
- **min_dimensions**: Minimum image dimensions to include (format: WIDTHxHEIGHT)

#### Analysis Options
- **analyze_filename**: Consider filename patterns when determining similarity
- **analyze_metadata**: Consider image metadata in similarity calculations
- **metadata_weight**: Weight given to metadata/filename vs hash similarity (0.0-1.0)
- **save_hashes**: Save computed hashes to image metadata for future use

#### Duplicate Handling
- **move_duplicates**: Legacy option for duplicate movement (use duplicate_action instead)
- **duplicate_action**: How to handle duplicates:
  - **move**: Move duplicate files to output folder
  - **copy**: Copy duplicate files to output folder
  - **none**: Don't modify files (analysis only)
- **output_folder**: Destination for moved/copied duplicates
- **group_by_similarity**: Organize duplicates by similarity level in output folder
- **keep_largest**: Keep the largest file when determining the base image

#### Result Options
- **update_metadata**: Add similarity information to image metadata
- **save_results**: Save analysis results to disk
- **results_format**: Format for saved results:
  - **json**: Detailed JSON format
  - **csv**: Simple CSV format for spreadsheet viewing
  - **both**: Save in both formats
- **display_top_n**: Number of duplicate groups to display in results (0-100)

## Output

- **duplicate_groups**: Text summary of detected duplicate groups
- **total_duplicates**: Total number of duplicate images found
- **stats_json**: Detailed statistics in JSON format
- **results_path**: Path to the saved results file

## Detailed Parameter Information

### Hash Algorithms

- **phash (Perceptual Hash)**: Considers the visual appearance of an image, resistant to minor visual changes. Best general-purpose algorithm for finding visually similar images.
- **average_hash**: Simple algorithm that uses average pixel values. Fast but less accurate than phash.
- **dhash (Difference Hash)**: Focuses on gradients within an image, good for detecting images with similar structures.
- **whash-haar (Wavelet Hash)**: Uses wavelet transforms to detect similarities at multiple scales.

### Similarity Thresholds

The node uses three levels of similarity thresholds:

- **exact_duplicate_threshold**: Images with similarity above this threshold are considered identical copies (recommended: 0.92-0.97)
- **similar_image_threshold**: Images with similarity above this threshold are considered visually similar but not exact duplicates (recommended: 0.80-0.90)
- **variant_threshold**: Images with similarity above this threshold are considered variations of the same content (recommended: 0.65-0.75)

### Metadata Integration

When **analyze_metadata** is enabled, the node examines image metadata for:

- Dimensions (to detect resized versions)
- Creation dates (to identify timeframes)
- AI generation parameters (seed, model) to identify variations from the same generation

When **save_hashes** is enabled, computed hashes are stored in image metadata, allowing faster processing in future runs.

### Organization Options

When moving or copying duplicates (**duplicate_action** set to "move" or "copy"):

- **group_by_similarity** creates separate folders for exact duplicates, similar images, and variants
- **keep_largest** determines which file to consider the "original" based on file size

## Usage Examples

### Basic Duplicate Detection

Set up the node with a folder path, select phash as the algorithm, and use default thresholds. This will identify duplicate images without modifying any files.

### Organizing a Large Image Collection

1. Set folder_path to your main image directory
2. Enable recursive to scan all subdirectories
3. Set duplicate_action to "move"
4. Set output_folder to "duplicates"
5. Enable group_by_similarity to organize by duplicate type
6. Run the node to clean up your collection while preserving originals

### Finding AI Image Variations

1. Set primary_hash to "phash"
2. Lower variant_threshold to around 0.7
3. Enable analyze_metadata to detect images with the same AI generation seed
4. Set metadata_weight to 0.3-0.5 to balance hash and metadata importance
5. Run to identify images generated from the same or similar prompts

### Creating a Detailed Report

1. Configure the node for your detection needs
2. Set save_results to True
3. Set results_format to "both"
4. Run the node to generate comprehensive reports (useful for large collections)

## Implementation Notes

- Uses the imagehash library for perceptual hash calculations
- Integrates with Eric's metadata system when available
- Processes images in batches for memory efficiency
- Implements Union-Find data structure for efficient grouping of similar images

## Dependencies

- **Required**: Python libraries: PIL (Pillow), numpy, tqdm
- **Optional**: imagehash library (will be prompted to install if missing)
- **Enhanced functionality**: Eric's metadata system (if available)

## Performance Considerations

- Processing speed depends on image count and dimensions
- Using saved hashes significantly speeds up repeated analysis
- Large collections may require significant memory

## Integration with Metadata System

This node integrates with the metadata system to:

1. Store computed hashes for faster future processing
2. Record similarity relationships between images
3. Enhance similarity detection using metadata attributes

## Troubleshooting

- If the node seems slow, try using average_hash for initial scans
- For large collections, scan in smaller batches using additional_folders
- Adjust thresholds if too many/few duplicates are detected
- Use save_hashes to speed up future analysis

# Differences Between Hash Algorithms

Each hash algorithm has different strengths and weaknesses for finding duplicate or similar images:

pHash (Perceptual Hash) is considered the most balanced and widely used algorithm, offering good accuracy while being relatively fast. It uses Discrete Cosine Transform (DCT) to convert images to frequency domains, making it robust against resizing, minor color adjustments, and compression artifacts.

Average Hash is the simplest and fastest algorithm. It works by resizing the image to a small square, calculating the average pixel value, and creating a binary hash based on whether pixels are above or below that average. It's great for exact duplicates but less effective for altered images.

dHash (Difference Hash) computes differences between adjacent pixels rather than absolute values. This makes it particularly good at detecting structural elements and edges, making it excellent for detecting images with brightness or contrast changes.

Wavelet Hash (whash-haar) is the most sophisticated of these algorithms, using wavelet decomposition to analyze images at different scales. It's best for detecting complex similarities between significantly modified images, though it's also the most computationally expensive.

# Best Two-Stage Combinations

For a two-stage approach, here are the best combinations:

1. **pHash + dHash**: This is likely the best general-purpose combination
   - pHash provides a good baseline for similarity
   - dHash complements by focusing on structural changes and edge differences
   - Both are relatively efficient while covering different types of modifications

2. **Average Hash + pHash**:
   - Fast initial screening with Average Hash
   - More accurate refinement with pHash
   - Good for large collections where performance matters

3. **pHash + Wavelet Hash**:
   - For maximum accuracy when performance is less critical
   - pHash catches most duplicates efficiently
   - Wavelet Hash refines results for heavily modified images

4. **Average Hash + dHash**:
   - Fastest combination with decent accuracy
   - Good complementary coverage of different image characteristics

For your current threshold values (0.985 for exact, 0.95 for variant, 0.92 for similar), pHash as primary and dHash as secondary would likely give you the best balance of accuracy and performance. This combination is particularly good at detecting both structural and perceptual similarities across different types of image modifications.