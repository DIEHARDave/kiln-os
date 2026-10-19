/* Read-only system queries: fast, file based, safe from the UI thread. */
#ifndef RUI_SYS_H
#define RUI_SYS_H

#include <stdbool.h>
#include <stddef.h>

/* IPv4 address of iface, or false */
bool sys_ip(const char *iface, char *buf, size_t cap);
/* First IPv4 of eth0, then wlan0, then any non-loopback */
bool sys_main_ip(char *buf, size_t cap, char *iface, size_t icap);

/* /dev path of a GPT partition by name (PARTNAME in sysfs) */
bool sys_part(const char *name, char *buf, size_t cap);

/* The ota boot flag ("ota:kernel2", ...); false if unreadable */
bool sys_ota_flag(char *buf, size_t cap);
/* Main OS root (slot B) holds a squashfs */
bool sys_main_installed(void);

/* Last non-empty line of the update log, and its age; false if none */
bool sys_last_update(char *buf, size_t cap);

/* USB storage */
typedef struct {
	char dev[64];		/* /dev/sda1 */
	char dir[160];		/* mount point, "" when not mounted */
	char fs[16];
	unsigned long long free_mb, size_mb;
} usb_vol;
int sys_usb_list(usb_vol *v, int max);	/* mounted first */

/* Files: name + size */
typedef struct {
	char path[256];
	char name[96];
	unsigned long long size;
	long mtime;
} file_ent;
int sys_list_swu(file_ent *f, int max);	/* update dir + USB top dirs */

/* Backup sets on mounted USB sticks: directories <stick>/ad5x-backup-<date>-<n>
 * with NAME.img[.NNN] partition images */
typedef struct {
	char path[256];
	char label[96];		/* directory name */
	char parts[16][24];	/* partition names from the image files */
	int nparts;
	unsigned long long size;
} backup_set;
int sys_list_backups(backup_set *b, int max);

void human_size(unsigned long long bytes, char *buf, size_t cap);

#endif
