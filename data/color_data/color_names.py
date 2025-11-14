"""
Color name definitions for accurate color naming in palette analysis.
"""

from typing import Dict, Tuple

# Function to get the complete color dictionary
def get_color_names() -> Dict[str, Tuple[int, int, int]]:
    """Get the complete dictionary of color names and RGB values"""
    colors = {}
    
    # Basic colors (Reds, Oranges, Yellows)
    basic_colors = {
        # Reds
        'red': (255, 0, 0),
        'crimson': (220, 20, 60),
        'firebrick': (178, 34, 34),
        'darkred': (139, 0, 0),
        'maroon': (128, 0, 0),
        'indian_red': (205, 92, 92),
        'salmon': (250, 128, 114),
        'light_coral': (240, 128, 128),
        'dark_salmon': (233, 150, 122),
        'light_salmon': (255, 160, 122),
        'scarlet': (255, 36, 0),
        'vermilion': (227, 66, 52),
        'burgundy': (128, 0, 32),
        'wine': (114, 47, 55),
        'ruby': (155, 17, 30),
        
        # Oranges
        'orange': (255, 165, 0),
        'dark_orange': (255, 140, 0),
        'coral': (255, 127, 80),
        'tomato': (255, 99, 71),
        'orange_red': (255, 69, 0),
        'tangerine': (242, 133, 0),
        'amber': (255, 191, 0),
        'apricot': (251, 206, 177),
        
        # Yellows
        'yellow': (255, 255, 0),
        'light_yellow': (255, 255, 224),
        'lemon_chiffon': (255, 250, 205),
        'gold': (255, 215, 0),
        'golden': (255, 215, 0),
        'cream_yellow': (255, 253, 208),
        'lemon': (255, 250, 115),
        'canary': (255, 255, 153),
        'mustard': (225, 173, 1),
        'honey': (227, 170, 67),
        'khaki': (240, 230, 140),
        'pale_goldenrod': (238, 232, 170),
        'light_goldenrod_yellow': (250, 250, 210),
        'dark_yellow': (139, 139, 0),
    }
    colors.update(basic_colors)

    # Greens
    greens = {
        'green': (0, 128, 0),
        'lime': (0, 255, 0),
        'lime_green': (50, 205, 50),
        'forest_green': (34, 139, 34),
        'dark_green': (0, 100, 0),
        'olive': (128, 128, 0),
        'olive_drab': (107, 142, 35),
        'sea_green': (46, 139, 87),
        'medium_sea_green': (60, 179, 113),
        'spring_green': (0, 255, 127),
        'olive_green': (107, 142, 35),
        'dark_olive': (85, 107, 47),
        'dark_olive_green': (85, 107, 47),
        'green_yellow': (173, 255, 47),
        'yellow_green': (154, 205, 50),
        'dark_sea_green': (143, 188, 143),
        'emerald': (0, 201, 87),
        'mint_green': (152, 255, 152),
        'jade': (0, 168, 107),
        'malachite': (11, 218, 81),
        'chartreuse': (127, 255, 0),
        'light_olive': (154, 166, 96),
        'moss_green': (134, 150, 99),
        'dark_moss': (74, 93, 35),
        'light_moss': (150, 153, 104),
        'sage': (138, 154, 131),
        'sage_green': (159, 174, 151),
        'light_sage': (188, 198, 182),
        'dark_sage': (115, 127, 109),
        'eucalyptus': (123, 155, 140),
        'fern_green': (84, 139, 84),
        'avocado': (118, 135, 67),
        'artichoke': (143, 151, 121),
        'pistachio': (144, 172, 120),
        'hunter_green': (53, 94, 59),
        'pine_green': (33, 90, 56),
        'spruce': (53, 88, 85),
        'tea_green': (208, 233, 202),
        'mint': (150, 222, 188),
        'light_mint': (188, 236, 215),
        'celadon': (175, 209, 183),
    }
    colors.update(greens)

    # Blues, Cyans, Teals
    blues = {
        'blue': (0, 0, 255),
        'navy': (0, 0, 128),
        'royal_blue': (65, 105, 225),
        'steel_blue': (70, 130, 180),
        'dark_blue': (0, 0, 139),
        'medium_blue': (0, 0, 205),
        'sky_blue': (135, 206, 235),
        'light_sky_blue': (135, 206, 250),
        'deep_sky_blue': (0, 191, 255),
        'dodger_blue': (30, 144, 255),
        'cornflower_blue': (100, 149, 237),
        'cadet_blue': (95, 158, 160),
        'medium_aquamarine': (102, 205, 170),
        'dark_cyan': (0, 139, 139),
        'aqua': (0, 255, 255),
        'cyan': (0, 255, 255),
        'light_cyan': (224, 255, 255),
        'teal': (0, 128, 128),
        'aquamarine': (127, 255, 212),
        'medium_turquoise': (72, 209, 204),
        'dark_turquoise': (0, 206, 209),
        'powder_blue': (176, 224, 230),
        'light_blue': (173, 216, 230),
        'light_steel_blue': (176, 196, 222),
        'pale_turquoise': (175, 238, 238),
        'midnight_blue': (25, 25, 112),
        'baby_blue': (137, 207, 240),
        'cornflower': (100, 149, 237),
        'periwinkle': (150, 163, 216),
        'slate_blue': (106, 90, 205),
        'cerulean': (0, 123, 167),
        'azure': (0, 127, 255),
        'turquoise': (64, 224, 208),
        'cobalt': (0, 71, 171),
    }
    colors.update(blues)

    # Purples and Pinks
    purples = {
        'purple': (128, 0, 128),
        'indigo': (75, 0, 130),
        'dark_magenta': (139, 0, 139),
        'dark_violet': (148, 0, 211),
        'dark_orchid': (153, 50, 204),
        'medium_purple': (147, 112, 219),
        'medium_orchid': (186, 85, 211),
        'magenta': (255, 0, 255),
        'orchid': (218, 112, 214),
        'violet': (238, 130, 238),
        'plum': (221, 160, 221),
        'lavender': (230, 230, 250),
        'lilac': (200, 162, 200),
        'mauve': (204, 153, 204),
        'amethyst': (153, 102, 204),
        'heliotrope': (187, 119, 255),
        'fuchsia': (255, 0, 255),
        'rose': (255, 0, 128),
        'shocking_pink': (252, 15, 192),
        'hot_pink': (255, 105, 180),
        'bubblegum': (255, 193, 204),
        'salmon_pink': (255, 145, 164),
        'coral_pink': (248, 131, 121),
        'peach': (255, 203, 164),
        'light_peach': (255, 229, 205),
    }
    colors.update(purples)

    # Earth tones and Browns
    earth_tones = {
        'brown': (165, 42, 42),
        'saddle_brown': (139, 69, 19),
        'sienna': (160, 82, 45),
        'chocolate': (210, 105, 30),
        'peru': (205, 133, 63),
        'sandy_brown': (244, 164, 96),
        'burly_wood': (222, 184, 135),
        'tan': (210, 180, 140),
        'taupe': (145, 133, 118),
        'light_taupe': (179, 164, 147),
        'warm_taupe': (171, 148, 126),
        'cool_taupe': (144, 141, 128),
        'khaki_brown': (110, 90, 55),
        'olive_brown': (94, 85, 24),
        'light_brown': (181, 136, 99),
        'medium_brown': (149, 107, 74),
        'dark_brown': (86, 57, 41),
        'chocolate_brown': (93, 63, 45),
        'golden_brown': (153, 101, 21),
        'espresso': (61, 39, 26),
        'coffee': (75, 60, 40),
        'coffee_brown': (75, 60, 40),
        'mocha': (103, 78, 57),
        'caramel': (194, 150, 90),
        'cinnamon': (167, 89, 29),
        'auburn': (154, 51, 1),
        'mahogany': (103, 26, 10),
        'sepia': (112, 66, 20),
        'rust': (183, 65, 14),
        'ochre': (204, 119, 34),
        'raw_sienna': (176, 101, 0),
        'burnt_sienna': (233, 116, 81),
        'raw_umber': (115, 74, 18),
        'burnt_umber': (138, 51, 36),
        'umber': (99, 81, 71),
        'terra_cotta': (226, 114, 91),
        'dust_brown': (180, 165, 140),
    }
    colors.update(earth_tones)

    # Tans, Beiges and Skin tones
    tans = {
        'sand': (222, 197, 158),
        'light_sand': (236, 213, 174),
        'dark_sand': (194, 170, 131),
        'wheat': (216, 187, 141),
        'cream': (255, 251, 214),
        'eggshell': (247, 245, 225),
        'buff': (240, 220, 130),
        'warm_tan': (214, 176, 121),
        'cool_tan': (209, 190, 156),
        'dark_tan': (181, 154, 118),
        'light_beige': (229, 212, 187),
        'beige': (213, 198, 175),
        'warm_beige': (221, 198, 166),
        'cool_beige': (206, 199, 184),
        'peach_puff': (255, 218, 185),
        'bisque': (255, 228, 196),
        'navajo_white': (255, 222, 173),
        'moccasin': (255, 228, 181),
        'papaya_whip': (255, 239, 213),
    }
    colors.update(tans)

    # Whites and Ivories
    whites = {
        'white': (255, 255, 255),
        'snow': (255, 250, 250),
        'honeydew': (240, 255, 240),
        'mint_cream': (245, 255, 250),
        'azure': (240, 255, 255),
        'alice_blue': (240, 248, 255),
        'ghost_white': (248, 248, 255),
        'white_smoke': (245, 245, 245),
        'seashell': (255, 245, 238),
        'linen': (250, 240, 230),
        'ivory': (255, 255, 240),
        'misty_rose': (255, 228, 225),
    }
    colors.update(whites)

    # Grays
    grays = {
        'gainsboro': (220, 220, 220),
        'light_gray': (211, 211, 211),
        'silver': (192, 192, 192),
        'dark_gray': (169, 169, 169),
        'gray': (128, 128, 128),
        'dim_gray': (105, 105, 105),
        'light_slate_gray': (119, 136, 153),
        'slate_gray': (112, 128, 144),
        'dark_slate_gray': (47, 79, 79),
        'black': (0, 0, 0),
        'warm_gray_1': (188, 175, 170),
        'warm_gray_2': (165, 151, 146),
        'warm_gray_3': (141, 128, 124),
        'warm_gray_4': (118, 106, 104),
        'warm_gray_5': (95, 85, 83),
        'warm_gray_6': (72, 65, 64),
        'warm_gray_7': (52, 46, 45),
        'cool_gray_1': (175, 180, 188),
        'cool_gray_2': (154, 159, 166),
        'cool_gray_3': (131, 136, 143),
        'cool_gray_4': (108, 113, 121),
        'cool_gray_5': (86, 90, 98),
        'cool_gray_6': (64, 68, 75),
        'cool_gray_7': (45, 48, 54),
        'neutral_gray_1': (182, 182, 182),
        'neutral_gray_2': (158, 158, 158),
        'neutral_gray_3': (135, 135, 135),
        'neutral_gray_4': (112, 112, 112),
        'neutral_gray_5': (89, 89, 89),
        'neutral_gray_6': (66, 66, 66),
        'neutral_gray_7': (43, 43, 43),
        'charcoal': (54, 56, 62),
        'charcoal_light': (76, 78, 86),
        'charcoal_dark': (38, 39, 43),
        'slate': (70, 80, 90),
        'light_slate': (100, 115, 130),
        'dark_slate': (45, 55, 65),
        'graphite': (50, 50, 55),
    }
    colors.update(grays)
    # Hair colors
    hair_colors = {
        'platinum_blonde': (222, 210, 180),
        'ash_blonde': (206, 197, 170),
        'golden_blonde': (219, 190, 138),
        'honey_blonde': (221, 179, 105),
        'strawberry_blonde': (225, 169, 115),
        'light_auburn': (170, 105, 79),
        'copper_red': (173, 92, 58),
        'ginger': (189, 94, 47),
        'chestnut': (117, 64, 42),
        'chocolate_hair': (87, 64, 53),
        'dark_auburn': (110, 52, 34),
        'light_brown_hair': (148, 111, 81),
        'medium_brown_hair': (113, 81, 58),
        'dark_brown_hair': (69, 51, 34),
        'black_brown_hair': (49, 36, 25),
        'jet_black_hair': (33, 26, 19),
        'ash_brown': (125, 102, 85),
        'golden_brown_hair': (154, 114, 75),
        'salt_and_pepper': (145, 145, 145),
        'silver_gray_hair': (193, 194, 193),
        'steel_gray_hair': (144, 145, 154),
        'white_hair': (235, 235, 235),
    }
    colors.update(hair_colors)

    # Wood and natural materials
    wood_colors = {
        'pine_wood': (200, 175, 125),
        'light_oak': (203, 167, 119),
        'oak': (184, 146, 95),
        'dark_oak': (157, 116, 73),
        'walnut': (115, 85, 63),
        'dark_walnut': (89, 66, 49),
        'cherry_wood': (155, 83, 70),
        'rosewood': (103, 49, 47),
        'mahogany_wood': (121, 59, 48),
        'ebony': (53, 40, 30),
        'birch': (215, 191, 160),
        'maple': (203, 170, 126),
        'cedar': (175, 120, 84),
        'teak': (145, 107, 70),
        'bamboo': (190, 175, 115),
        'driftwood': (176, 169, 152),
        'redwood': (162, 94, 75),
        'ash_wood': (203, 191, 169),
        'hickory': (189, 157, 112),
        'weathered_wood': (159, 156, 138),
        'bark_brown': (89, 71, 57),
        'dark_bark': (66, 55, 46),
    }
    colors.update(wood_colors)

    # Extended skin tones
    skin_tones = {
        # Light skin tones
        'porcelain': (251, 237, 220),
        'fair': (245, 226, 201),
        'light_ivory': (245, 222, 188),
        'warm_ivory': (243, 215, 178),
        'sand_beige': (236, 211, 175),
        'peach': (239, 206, 171),
        'light_rose_beige': (233, 195, 165),
        'light_golden_beige': (226, 193, 154),
        
        # Medium skin tones
        'olive_beige': (207, 178, 143),
        'honey_beige': (216, 185, 146),
        'amber_beige': (203, 166, 125),
        'warm_beige_skin': (216, 181, 141),
        'golden_tan': (214, 175, 130),
        'caramel': (202, 158, 112),
        'medium_olive': (185, 156, 122),
        'golden_brown_skin': (193, 151, 104),
        
        # Deeper skin tones
        'toffee': (178, 137, 95),
        'almond': (163, 123, 91),
        'amber_brown': (151, 109, 74),
        'chestnut_skin': (146, 104, 78),
        'copper_brown': (140, 91, 62),
        'cinnamon': (153, 97, 64),
        'sienna_skin': (138, 86, 58),
        'mahogany_skin': (118, 74, 50),
        
        # Deepest skin tones
        'deep_golden_brown': (124, 79, 52),
        'dark_chocolate': (93, 58, 39),
        'espresso_skin': (74, 47, 35),
        'deep_espresso': (58, 36, 27),
        'ebony_skin': (47, 30, 23),
    }
    colors.update(skin_tones)

    # Earth and soil colors
    earth_colors = {
        'clay': (163, 124, 99),
        'terracotta_soil': (178, 111, 70),
        'adobe': (169, 116, 83),
        'red_clay': (154, 85, 55),
        'potting_soil': (64, 50, 36),
        'garden_soil': (81, 63, 43),
        'dark_loam': (52, 41, 28),
        'peat': (68, 55, 38),
        'sandy_soil': (170, 145, 104),
        'dark_earth': (42, 36, 29),
        'rich_soil': (75, 57, 41),
        'wet_earth': (58, 44, 31),
    }
    colors.update(earth_colors)

    # Stone and mineral colors
    stone_colors = {
        'sandstone': (200, 186, 149),
        'limestone': (203, 196, 172),
        'slate_stone': (105, 109, 113),
        'granite': (168, 162, 159),
        'dark_granite': (114, 114, 114),
        'basalt': (73, 74, 78),
        'marble': (229, 220, 207),
        'travertine': (209, 199, 172),
        'soapstone': (158, 164, 166),
        'quartz': (225, 222, 220),
        'onyx': (53, 52, 55),
        'flint': (108, 102, 98),
        'shale': (91, 89, 84),
    }
    colors.update(stone_colors)

    metallic_colors = {
        'silver_metallic': (192, 192, 192),
        'chrome': (226, 226, 226),
        'brushed_aluminum': (176, 176, 180),
        'gold_metallic': (212, 175, 55),
        'rose_gold': (183, 110, 121),
        'bronze': (205, 127, 50),
        'copper_metallic': (184, 115, 51),
        'brass': (181, 166, 66),
        'pewter': (132, 132, 136),
        'platinum': (229, 228, 226),
        'gunmetal': (42, 52, 57),
        'steel_blue_metallic': (79, 148, 205),
        'titanium': (135, 134, 129),
        'antique_brass': (205, 149, 117),
        'antique_bronze': (102, 93, 30),
        'antique_copper': (150, 90, 62),
    }
    colors.update(metallic_colors)

    faded_colors = {
        'faded_red': (171, 78, 82),
        'faded_blue': (121, 135, 161),
        'faded_green': (136, 156, 121),
        'faded_yellow': (211, 206, 127),
        'faded_purple': (157, 138, 163),
        'faded_teal': (119, 163, 165),
        'faded_pink': (222, 165, 178),
        'faded_orange': (221, 154, 99),
        'faded_denim': (131, 152, 173),
        'faded_khaki': (195, 181, 152),
        'faded_olive': (154, 153, 107),
        'vintage_blue': (103, 142, 171),
        'vintage_red': (182, 92, 77),
        'vintage_green': (121, 148, 110),
        'vintage_yellow': (233, 215, 142),
        'vintage_pink': (223, 179, 191),
        'washed_denim': (149, 169, 190),
        'dusty_rose': (193, 135, 138),
        'dusty_blue': (135, 157, 173),
        'dusty_green': (132, 155, 135),
        'dusty_lavender': (172, 160, 187),
        'sun_bleached_brown': (169, 146, 126),
        'weathered_blue': (139, 153, 173),
        'weathered_green': (148, 161, 139),
        'patina': (124, 172, 157),
    }
    colors.update(faded_colors)

    # Iridescent colors
    iridescent_colors = {
        'opal': (167, 198, 218),
        'mother_of_pearl': (242, 241, 235),
        'abalone': (215, 225, 200),
        'pearl': (234, 224, 200),
        'iridescent_blue': (150, 189, 225),
        'iridescent_pink': (232, 179, 213),
        'iridescent_purple': (178, 161, 224),
        'iridescent_green': (157, 222, 202),
        'oil_slick_blue': (44, 117, 255),
        'oil_slick_purple': (126, 38, 223),
        'oil_slick_green': (0, 233, 185),
        'holographic_silver': (216, 216, 224),
        'rainbow_sheen': (191, 175, 223),
        'prismatic': (188, 188, 220),
    }
    colors.update(iridescent_colors)

    display_colors = {
        'screen_blue': (0, 122, 204),
        'monitor_black': (20, 20, 20),
        'led_red': (255, 17, 0),
        'led_green': (0, 255, 42),
        'led_blue': (0, 68, 255),
        'lcd_cyan': (0, 217, 228),
        'lcd_magenta': (246, 0, 255),
        'terminal_green': (0, 255, 65),
        'night_mode_amber': (255, 180, 0),
        'digital_yellow': (255, 216, 0),
        'pixel_purple': (187, 0, 255),
        'backlight_blue': (61, 180, 242),
        'interface_gray': (240, 240, 240),
        'dark_mode_gray': (54, 54, 54),
    }
    colors.update(display_colors)

    painterly_colors = {
        'cadmium_red': (227, 0, 34),
        'alizarin_crimson': (227, 38, 54),
        'cobalt_violet': (159, 63, 176),
        'ultramarine_blue': (65, 102, 245),
        'prussian_blue': (0, 49, 83),
        'phthalo_blue': (0, 15, 137),
        'phthalo_green': (0, 86, 59),
        'sap_green': (80, 125, 42),
        'cadmium_yellow': (255, 211, 0),
        'naples_yellow': (251, 233, 165),
        'burnt_sienna_paint': (233, 116, 81),
        'raw_sienna_paint': (188, 143, 86),
        'raw_umber_paint': (130, 102, 68),
        'burnt_umber_paint': (128, 70, 27),
        'vandyke_brown': (106, 81, 59),
        'titanium_white': (252, 252, 252),
        'ivory_black': (41, 41, 41),
        'ochre_paint': (204, 119, 34),
        'cerulean_blue': (0, 123, 167),
        'quinacridone_magenta': (178, 66, 106),
        'hookers_green': (0, 112, 60),
        'permanent_green': (4, 113, 35),
        'vermilion': (217, 56, 30),
        'viridian': (64, 130, 109),
    }
    colors.update(painterly_colors)

    muted_colors = {
        'slate_blue_gray': (119, 133, 157),
        'taupe_gray': (138, 129, 124),
        'sage_gray': (128, 135, 129),
        'moss_gray': (134, 141, 113),
        'smoke_gray': (151, 148, 153),
        'ash_gray': (154, 156, 155),
        'heather_gray': (166, 168, 171),
        'stormy_blue': (92, 113, 140),
        'dusty_teal': (96, 142, 145),
        'matte_navy': (41, 65, 94),
        'soft_burgundy': (135, 69, 80),
        'muted_plum': (133, 103, 124),
        'subdued_olive': (122, 124, 85),
        'faded_terracotta': (175, 110, 93),
        'quiet_coral': (214, 138, 118),
        'charcoal_blue': (61, 72, 88),
        'pewter_green': (105, 128, 126),
        'muted_cyan': (122, 175, 185),
        'desaturated_navy': (63, 76, 98),
        'desaturated_teal': (91, 136, 135),
        'office_blue': (79, 129, 189),
        'conference_room_gray': (214, 214, 214),
        'corporate_navy': (31, 58, 88),
        'business_green': (74, 111, 94),
    }
    colors.update(muted_colors)

    # Highly saturated primary and secondary colors
    vibrant_colors = {
        # Reds
        'pure_red': (255, 0, 0),
        'bright_red': (255, 36, 0),
        'vivid_red': (246, 0, 0),
        'candy_red': (255, 8, 64),
        'cherry_red': (215, 0, 25),
        'cardinal_red': (196, 30, 58),
        'neon_red': (255, 7, 58),
        
        # Oranges
        'pure_orange': (255, 127, 0),
        'bright_orange': (255, 140, 0),
        'vivid_orange': (255, 117, 24),
        'electric_orange': (255, 87, 34),
        'neon_orange': (255, 103, 0),
        'fluorescent_orange': (255, 127, 42),
        
        # Yellows
        'pure_yellow': (255, 255, 0),
        'bright_yellow': (255, 246, 0),
        'lemon_yellow': (255, 244, 0),
        'canary_yellow': (255, 255, 102),
        'sunshine_yellow': (255, 236, 0),
        'neon_yellow': (255, 255, 0),
        'fluorescent_yellow': (255, 247, 0),
        
        # Greens
        'pure_green': (0, 255, 0),
        'bright_green': (0, 235, 0),
        'vivid_green': (0, 250, 0),
        'electric_green': (0, 255, 42),
        'neon_green': (57, 255, 20),
        'fluorescent_green': (0, 255, 127),
        'signal_green': (0, 195, 0),
        
        # Blues
        'pure_blue': (0, 0, 255),
        'bright_blue': (0, 102, 255),
        'vivid_blue': (0, 0, 240),
        'electric_blue': (0, 142, 255),
        'neon_blue': (0, 123, 255),
        'cobalt_blue': (0, 71, 171),
        'ultramarine': (18, 10, 230),
        'royal_blue_vibrant': (65, 105, 225),
        
        # Purples
        'pure_purple': (128, 0, 128),
        'bright_purple': (144, 0, 255),
        'vivid_purple': (143, 0, 255),
        'electric_purple': (191, 0, 255),
        'neon_purple': (118, 0, 237),
        'fluorescent_purple': (210, 0, 255),
        
        # Magentas
        'pure_magenta': (255, 0, 255),
        'bright_magenta': (255, 0, 211),
        'vivid_magenta': (255, 0, 186),
        'neon_magenta': (255, 0, 255),
        'shocking_pink_vibrant': (255, 0, 140),
        
        # Other vibrant colors
        'neon_pink': (255, 0, 187),
        'hot_pink_vibrant': (255, 0, 170),
        'acid_green': (187, 255, 0),
        'chartreuse_bright': (213, 255, 0),
        'laser_lemon': (254, 254, 34),
        'neon_coral': (255, 80, 75),
        'electric_indigo': (111, 0, 255),
        'bright_turquoise': (0, 245, 255),
        'brilliant_azure': (50, 139, 255),
        'aqua_vibrant': (0, 255, 255),
        'teal_bright': (0, 213, 197),
    }
    colors.update(vibrant_colors)
    # Fluorescent and neon variants
    neon_colors = {
        'neon_lime': (186, 255, 0),
        'highlighter_yellow': (239, 255, 0),
        'highlighter_green': (0, 255, 127),
        'highlighter_pink': (255, 105, 255),
        'highlighter_blue': (0, 224, 255),
        'highlighter_orange': (255, 165, 0),
        'neon_mint': (0, 255, 170),
        'glow_green': (0, 255, 0),
        'radioactive_green': (118, 255, 0),
        'laser_blue': (0, 240, 255),
        'plasma_pink': (255, 0, 153),
        'electric_violet': (140, 0, 255),
        'nuclear_green': (57, 255, 20),
        'lightning_yellow': (255, 252, 0),
    }

    colors.update(neon_colors)

    # Try to add webcolors if available
    try:
        import webcolors
        for name, hex_value in webcolors.CSS3_NAMES_TO_HEX.items():
            rgb = webcolors.hex_to_rgb(hex_value)
            colors[name.lower().replace('-', '_')] = rgb
    except (ImportError, AttributeError):
        # If webcolors is not available, just use our base dictionary
        pass
    
    return colors

# Pre-processed complete color dictionary for direct import
COLOR_NAMES = get_color_names()