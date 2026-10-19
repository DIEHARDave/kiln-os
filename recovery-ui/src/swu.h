/* SWUpdate progress, from the daemon's progress socket (any source: our
 * swupdate-client run, the web upload on :8080, ...). A thread stays
 * connected (reconnecting every second) and keeps the latest state. */
#ifndef RUI_SWU_H
#define RUI_SWU_H

#include <stdbool.h>
#include <stddef.h>

typedef enum {
	SWU_IDLE, SWU_START, SWU_RUN, SWU_SUCCESS, SWU_FAILURE,
	SWU_DOWNLOAD, SWU_DONE, SWU_SUBPROCESS, SWU_PROGRESS
} swu_status;		/* = SWUpdate's RECOVERY_STATUS */

typedef enum {
	SWU_SRC_UNKNOWN, SWU_SRC_WEBSERVER, SWU_SRC_SURICATTA,
	SWU_SRC_DOWNLOADER, SWU_SRC_LOCAL, SWU_SRC_CHUNKS
} swu_source;		/* = SWUpdate's sourcetype */

typedef struct {
	unsigned seq;		/* bumps with every message */
	bool connected;
	swu_status status;	/* last status other than SWU_PROGRESS (info) */
	swu_source source;
	unsigned nsteps, cur_step, cur_percent, dwl_percent;
	int overall;		/* 0..100 over all steps */
	char image[128];
	char handler[64];
	char info[256];		/* last info text */
	unsigned info_seq;
	bool active;		/* an update is in progress */
	swu_status result;	/* last SWU_SUCCESS / SWU_FAILURE seen */
	unsigned result_seq;	/* bumps with each result */
	swu_status last_logged;	/* (internal) */
	unsigned last_step;
} swu_state;

void swu_start(const char *socket_path);
void swu_get(swu_state *s);
const char *swu_status_name(swu_status s);
/* SWUpdate's messages since the last update started, one per line */
void swu_log_copy(char *buf, size_t cap);
/* Feed a fake message (screenshots, tests) */
void swu_inject(swu_status status, swu_source src, unsigned nsteps,
		unsigned cur_step, unsigned cur_percent, const char *image,
		const char *info);

#endif
