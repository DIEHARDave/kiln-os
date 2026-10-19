/* LVGL v9 configuration for ad5x-recovery-ui. Anything not set here takes
 * LVGL's default (lv_conf_internal.h). The back end is chosen by the
 * Makefile: RUI_FBDEV (panel: fbdev + evdev), RUI_SDL (laptop window) or
 * neither (headless, screenshots only). */
#ifndef LV_CONF_H
#define LV_CONF_H

/* The AD5X panel is 800x480 XRGB8888 (32 bpp) */
#define LV_COLOR_DEPTH 32

/* glibc's malloc/string/printf: no fixed LVGL heap to size */
#define LV_USE_STDLIB_MALLOC  LV_STDLIB_CLIB
#define LV_USE_STDLIB_STRING  LV_STDLIB_CLIB
#define LV_USE_STDLIB_SPRINTF LV_STDLIB_CLIB

/* LVGL runs on the main thread only; workers hand data over under a mutex */
#define LV_USE_OS LV_OS_NONE
#define LV_DEF_REFR_PERIOD 33

#define LV_USE_LOG 1
#define LV_LOG_LEVEL LV_LOG_LEVEL_WARN
#define LV_LOG_PRINTF 0   /* main.c prints (filtered) */

#define LV_USE_DRAW_SW 1
#define LV_DRAW_SW_DRAW_UNIT_CNT 1
#define LV_USE_DRAW_SW_ASM LV_DRAW_SW_ASM_NONE
#define LV_DRAW_SW_COMPLEX 1

/* Glyph cache for Tiny TTF */
#define LV_CACHE_DEF_SIZE 0

/* Icons only: LV_SYMBOL_* glyphs, used as the fallback of the Noto fonts */
#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_16 1
#define LV_FONT_MONTSERRAT_20 1
#define LV_FONT_MONTSERRAT_24 1
#define LV_FONT_MONTSERRAT_28 1
#define LV_FONT_MONTSERRAT_40 1
#define LV_FONT_DEFAULT &lv_font_montserrat_20

/* Noto Sans, embedded TTF rendered at run time */
#define LV_USE_TINY_TTF 1
#define LV_TINY_TTF_FILE_SUPPORT 0
#define LV_TINY_TTF_CACHE_GLYPH_CNT 512
#define LV_TINY_TTF_CACHE_KERNING_CNT 512

#define LV_USE_THEME_DEFAULT 1
#define LV_THEME_DEFAULT_DARK 1
#define LV_THEME_DEFAULT_GROW 0
#define LV_THEME_DEFAULT_TRANSITION_TIME 60

#define LV_USE_QRCODE 1
#define LV_USE_SNAPSHOT 0
#define LV_USE_OBSERVER 1
#define LV_USE_SYSMON 0
#define LV_LABEL_LONG_TXT_HINT 1

/* Unused widgets/libs off (smaller binary) */
#define LV_USE_ANIMIMG 0
#define LV_USE_CALENDAR 0
#define LV_USE_CANVAS 1   /* lv_qrcode needs it */
#define LV_USE_CHART 0
#define LV_USE_IMAGEBUTTON 0
#define LV_USE_KEYBOARD 0
#define LV_USE_LED 0
#define LV_USE_MENU 0
#define LV_USE_ROLLER 0
#define LV_USE_SCALE 0
#define LV_USE_SPAN 0
#define LV_USE_SPINBOX 0
#define LV_USE_TILEVIEW 0
#define LV_USE_WIN 0
#define LV_USE_ARCLABEL 0
#define LV_USE_LOTTIE 0
#define LV_USE_THORVG_INTERNAL 0
#define LV_BUILD_EXAMPLES 0
#define LV_BUILD_DEMOS 0

/* Back ends */
#ifdef RUI_FBDEV
#define LV_USE_LINUX_FBDEV 1
#define LV_LINUX_FBDEV_BSD 0
#define LV_LINUX_FBDEV_RENDER_MODE LV_DISPLAY_RENDER_MODE_PARTIAL
#define LV_LINUX_FBDEV_BUFFER_COUNT 2
#define LV_LINUX_FBDEV_BUFFER_SIZE 120
#define LV_USE_EVDEV 1
#else
#define LV_USE_LINUX_FBDEV 0
#define LV_USE_EVDEV 0
#endif

#ifdef RUI_SDL
#define LV_USE_SDL 1
#define LV_SDL_INCLUDE_PATH <SDL2/SDL.h>
#define LV_SDL_RENDER_MODE LV_DISPLAY_RENDER_MODE_DIRECT
#define LV_SDL_BUF_COUNT 1
#define LV_SDL_ACCELERATED 1
#define LV_SDL_FULLSCREEN 0
#define LV_SDL_DIRECT_EXIT 1
#define LV_SDL_MOUSEWHEEL_MODE LV_SDL_MOUSEWHEEL_MODE_ENCODER
#else
#define LV_USE_SDL 0
#endif

#endif /* LV_CONF_H */
