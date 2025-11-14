# WordCloud Generator Node Documentation

## Overview
The WordCloud Generator Node is a comprehensive text visualization tool for ComfyUI that creates beautiful word clouds with extensive customization options. It leverages your metadata system's rich color database and cultural color data to provide meaningful color choices.

## Features

### 1. Color Options
- **Single Color**: Use one color for all words
- **Named Color**: Choose from 1300+ named colors from your color database
- **Random Colors**: Standard wordcloud random coloring
- **Cultural Color Sets**: Colors based on cultural significance and flag combinations
- **Emotional Color Sets**: Colors that evoke specific emotions
- **Color Harmonies**: Complementary color schemes based on color theory
- **Custom Range**: Specify your own comma-separated list of colors

#### Cultural Color Sets Include:
- Christmas/Holiday combinations (Red, Green, Gold, White)
- Pan-African colors (Green, Yellow, Red)
- Islamic colors (Green and White)
- Scandinavian themes (Blue, White, Gold)
- Regional themes (Western, Eastern, Chinese, Japanese, etc.)

#### Color Harmonies Include:
- Warm harmony (oranges, reds, yellows)
- Cool harmony (blues, cyans, greens)
- Pastel harmony (soft, muted tones)
- Earth harmony (browns, tans, naturals)
- Jewel harmony (deep, rich colors)

### 2. Font Options
- **Single Font**: Use one font for all words
- **Random Font per Cloud**: Choose one random font for the entire cloud
- **Random Font per Word**: Different font for each word (experimental)
- **Font Set**: Specify multiple fonts to choose from
- **Font Preview**: Generate preview images showing available fonts

### 3. Layout and Positioning
- **Orientation Control**: Horizontal preference ratio
- **Vertical Text**: Enable/disable vertical word placement
- **Upside Down**: Allow inverted text
- **Diagonal**: Enable diagonal text placement
- **Margins**: Control spacing around canvas edges
- **Word Spacing**: Adjust spacing between words

### 4. Text Processing
- **Include Numbers**: Whether to include numeric values
- **Normalize Plurals**: Remove trailing 's' from words
- **Collocations**: Include word pairs/phrases
- **Min Word Length**: Filter out short words
- **Collocation Threshold**: Sensitivity for phrase detection
- **Custom Stopwords**: Add your own words to exclude

### 5. Special Words and Phrases
- **JSON Configuration**: Specify special positioning and styling for important words
- **Position Control**: Place words at specific locations (center, top_left, etc.)
- **Size Multipliers**: Make special words larger or smaller
- **Custom Colors**: Override colors for specific words

Example special words configuration:
```json
{
    "IMPORTANT": {
        "position": "center",
        "size_multiplier": 2.0,
        "color": "#FF0000"
    },
    "\"key phrase\"": {
        "position": "top_center",
        "size_multiplier": 1.5,
        "color": "#00FF00"
    }
}
```

### 6. Background Options
- **Transparent**: Create overlay-ready transparent background
- **Solid Color**: Use specified background color
- **Background Opacity**: Control background transparency

### 7. Preview Modes
- **Font Preview**: Show available fonts with sample text
- **Color Preview**: Display selected color palette with cultural context
- **Pagination**: Navigate through font previews

### 8. Advanced Options
- **Relative Scaling**: Balance between word frequency and rank
- **Repeat Words**: Fill space by repeating words
- **Random Seed**: Reproducible results
- **Text File Input**: Load text from external .txt files

## Color Database Integration

The node integrates with your comprehensive color database containing:
- **1300+ Named Colors**: From "Absolute Zero" to "Zombie Green"
- **Cultural Significance Data**: How colors are perceived across different cultures
- **Color Combinations**: Traditional color pairings with historical context
- **Regional Themes**: Colors organized by geographic/cultural regions

## Usage Tips

1. **For Professional Documents**: Use "professional" emotional set or "minimalist_mono"
2. **For Celebrations**: Try "christmas_traditional" or cultural sets matching the occasion
3. **For Nature Themes**: Use "forest_greens", "earth_tones", or "nature_inspired"
4. **For Creative Projects**: Experiment with "creative" emotional set or "retro_80s"
5. **For Cultural Sensitivity**: Choose appropriate cultural color sets based on your audience

## Technical Notes

- Requires `wordcloud` library: `pip install wordcloud`
- Automatically discovers system fonts
- Supports transparent backgrounds for compositing
- Returns RGBA format images compatible with ComfyUI
- Includes debug output for troubleshooting
- Graceful fallbacks if libraries are missing

## Output

The node provides two outputs:
1. **WordCloud**: The generated word cloud image
2. **Preview**: Font preview or color preview when those modes are enabled

Both outputs are in ComfyUI-compatible RGBA format and can be used with other image processing nodes.
