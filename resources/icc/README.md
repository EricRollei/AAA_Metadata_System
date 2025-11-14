# ICC Profiles

This directory contains reference information about ICC color profiles. The actual profiles used by the Metadata_system nodes are located in:

`Metadata_System/nodes/profiles/`

## Default Profiles

The system looks for the following profiles:

- `sRGB_ICC_v4_Appearance.icc` - Default sRGB profile with appearance intent
- `sRGB_v4_ICC_preference.icc` - sRGB profile with preference intent
- `sRGB_v4_ICC_preference_displayclass.icc` - sRGB profile with display class
- `AdobeRGB1998.icc` - Adobe RGB (1998) profile
- `ProPhoto.icm` - ProPhoto RGB profile

## Profile Loading Process

The system will:
1. First look in the `nodes/profiles` directory 
2. Then check standard system locations if needed
3. As a last resort, generate a basic sRGB profile

## Sources

You can download standard ICC profiles from:

1. ICC: http://www.color.org/
2. Adobe: https://www.adobe.com/support/downloads/iccprofiles/iccprofiles_win.html
