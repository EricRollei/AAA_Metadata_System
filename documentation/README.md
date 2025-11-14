# ICC Profiles

This directory contains ICC color profiles used by the Metadata_system nodes.

## Default Profiles

The system looks for the following profiles:

- `sRGB_ICC_v4_Appearance.icc` - Default sRGB profile with appearance intent
- `sRGB_v4_ICC_preference.icc` - sRGB profile with preference intent
- `sRGB_v4_ICC_preference_displayclass.icc` - sRGB profile with display class
- `AdobeRGB1998.icc` - Adobe RGB (1998) profile
- `ProPhoto.icm` - ProPhoto RGB profile

## Sources

You can download standard ICC profiles from:

1. ICC: http://www.color.org/
2. Adobe: https://www.adobe.com/support/downloads/iccprofiles/iccprofiles_win.html

If no profiles are found here, the system will search in standard system locations
and fall back to generating a basic sRGB profile.
