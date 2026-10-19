// SPDX-License-Identifier: GPL-2.0
/*
 * Flashforge AD5X 7" 800x480 "KX070" panel on the X2600 LVDS output,
 * for the Ingenic SDK 6.6 fb_stage_wip framebuffer (ingenicfb).
 *
 * Modelled on displays/panel-hc101i35.c (LVDS VESA). Parameters recovered
 * from the stock 5.10 out-of-tree lcd_kx070.ko / soc_fb.ko (see
 * ad5x/ad5x-display.dtsi for the derivation). Shows HelixScreen on the AD5X.
 *
 * Copied to module_drivers/drivers/video/fbdev/ingenic/displays/ by
 * ad5x/build.sh; Kconfig/Makefile hooks: ad5x/patches/0001-*.patch.
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
#include <linux/lcd.h>
#include <linux/fb.h>

#include "../include/ingenicfb.h"
#include "../include/jz_dsim.h"

/*
 * 31.0 MHz: nearest entry of the SDK LVDS tables (jz_mipi_dsi_phy.c
 * lvds_pll_param_tab and fb_stage_wip/dpu_ctrl.c pclk_epll_tab both need
 * an exact match). Stock computed 976 * 531 * 60 = 31.095 MHz.
 * Refresh therefore ends up at 59.8 Hz.
 */
#define KX070_PIXCLK_KHZ	31000

struct kx070_dev {
	struct device *dev;
	struct lcd_device *lcd;
	int power;
	/* optional, absent on the AD5X (stock gpio_lcd_* = -1) */
	struct gpio_desc *rst;		/* "ingenic,rst-gpio" */
	struct gpio_desc *vdd_en;	/* "ingenic,vdd-en-gpio" */
};

static struct kx070_dev *kx070;

static void kx070_power_on(void *ppanel)
{
	if (kx070->vdd_en)
		gpiod_set_value_cansleep(kx070->vdd_en, 1);
	if (kx070->rst) {
		gpiod_set_value_cansleep(kx070->rst, 1);
		msleep(10);
		gpiod_set_value_cansleep(kx070->rst, 0);
		msleep(20);
	}
}

static void kx070_power_off(void *ppanel)
{
	if (kx070->vdd_en)
		gpiod_set_value_cansleep(kx070->vdd_en, 0);
}

static struct lcd_panel_ops kx070_ops = {
	.enable = kx070_power_on,
	.disable = kx070_power_off,
};

/* Stock lcd_kx070 lcdc_data.fb_mode, verbatim except pixclock. */
static struct fb_videomode kx070_modes[] = {
	{
		.name = "kx070",
		.refresh = 60,
		.xres = 800,
		.yres = 480,
		.pixclock = 0,		/* derived by ingenicfb from refresh */
		.left_margin = 88,	/* HBP */
		.right_margin = 40,	/* HFP */
		.hsync_len = 48,
		.upper_margin = 35,	/* VBP */
		.lower_margin = 13,	/* VFP */
		.vsync_len = 3,
		.sync = FB_SYNC_HOR_HIGH_ACT | FB_SYNC_VERT_HIGH_ACT,
		.vmode = FB_VMODE_NONINTERLACED,
		.flag = 0,
	},
};

static struct jzdsi_data kx070_dsi_pdata = {
	.modes = &kx070_modes[0],
	/* used by the LVDS clock/PLL setup, kHz */
	.video_config.pixel_clock = KX070_PIXCLK_KHZ,
	.video_config.virtual_channel = 0,
	.video_config.color_coding = COLOR_CODE_24BIT,	/* REG0C bit5, as stock */
	.video_config.video_mode = VIDEO_BURST_WITH_SYNC_PULSES,
	.video_config.receive_ack_packets = 0,
	.video_config.is_18_loosely = 0,
	/* stock LVDS polarity words were all "1" => REG0C bits 2..0 clear */
	.video_config.h_polarity = 0,
	.video_config.v_polarity = 0,
	.video_config.data_en_polarity = 0,
	.video_config.byte_clock = 0,
	.video_config.byte_clock_coef = MIPI_PHY_BYTE_CLK_COEF_MUL6_DIV5,
	/* dsi_config is unused in LVDS mode; values as the SDK LVDS panels */
	.dsi_config.max_lanes = 4,
	.dsi_config.max_hs_to_lp_cycles = 100,
	.dsi_config.max_lp_to_hs_cycles = 40,
	.dsi_config.max_bta_cycles = 4095,
	.dsi_config.color_mode_polarity = 1,
	.dsi_config.shut_down_polarity = 1,
	.dsi_config.max_bps = 2750,
	.bpp_info = 24,
};

static struct tft_config kx070_tft_cfg = {
	.pix_clk_inv = 0,
	.de_dl = 0,
	.sync_dl = 0,
	.vsync_dl = 0,
	.color_even = TFT_LCD_COLOR_EVEN_RGB,
	.color_odd = TFT_LCD_COLOR_ODD_RGB,
	.mode = TFT_LCD_MODE_PARALLEL_888,
};

static struct lcd_panel kx070_panel = {
	.name = "kx070",
	.num_modes = ARRAY_SIZE(kx070_modes),
	.modes = kx070_modes,
	.dsi_pdata = &kx070_dsi_pdata,
	.lcd_type = LCD_TYPE_LVDS_VESA,		/* stock: lvds format word 0 = VESA */
	.tft_config = &kx070_tft_cfg,
	.bpp = 32,
	.width = 108,				/* mm, stock lcdc_data */
	.height = 64,
	.dither_enable = 0,
	.ops = &kx070_ops,
};

static int kx070_set_power(struct lcd_device *lcd, int power)
{
	return 0;
}

static int kx070_get_power(struct lcd_device *lcd)
{
	struct kx070_dev *d = lcd_get_data(lcd);

	return d->power;
}

static struct lcd_ops kx070_lcd_ops = {
	.set_power = kx070_set_power,
	.get_power = kx070_get_power,
};

static int kx070_probe(struct platform_device *pdev)
{
	int ret;

	kx070 = devm_kzalloc(&pdev->dev, sizeof(*kx070), GFP_KERNEL);
	if (!kx070)
		return -ENOMEM;
	kx070->dev = &pdev->dev;
	kx070->power = FB_BLANK_POWERDOWN;
	dev_set_drvdata(&pdev->dev, kx070);

	/* gpiolib also matches the SDK's singular "<name>-gpio" spelling */
	kx070->rst = devm_gpiod_get_optional(&pdev->dev, "ingenic,rst", GPIOD_OUT_LOW);
	if (IS_ERR(kx070->rst))
		return PTR_ERR(kx070->rst);
	kx070->vdd_en = devm_gpiod_get_optional(&pdev->dev, "ingenic,vdd-en", GPIOD_OUT_LOW);
	if (IS_ERR(kx070->vdd_en))
		return PTR_ERR(kx070->vdd_en);

	kx070->lcd = devm_lcd_device_register(&pdev->dev, "kx070", &pdev->dev,
					      kx070, &kx070_lcd_ops);
	if (IS_ERR(kx070->lcd))
		return PTR_ERR(kx070->lcd);

	ret = ingenicfb_register_panel(&kx070_panel);
	if (ret < 0) {
		dev_err(&pdev->dev, "failed to register lcd panel: %d\n", ret);
		return ret;
	}

	return 0;
}

static const struct of_device_id kx070_of_match[] = {
	{ .compatible = "ingenic,kx070", },
	{ },
};
MODULE_DEVICE_TABLE(of, kx070_of_match);

static struct platform_driver kx070_driver = {
	.probe = kx070_probe,
	.driver = {
		.name = "panel-kx070",
		.of_match_table = kx070_of_match,
	},
};
module_platform_driver(kx070_driver);

MODULE_DESCRIPTION("Flashforge AD5X KX070 800x480 LVDS panel (Ingenic fb)");
MODULE_LICENSE("GPL");
