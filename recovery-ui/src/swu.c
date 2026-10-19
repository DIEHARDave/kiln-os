/* SWUpdate progress client (see swu.h).
 *
 * With USE_LIBSWUPDATE (the Buildroot build when SWUpdate is in the image)
 * it uses SWUpdate's own client library, libswupdate (progress_ipc.h).
 * Otherwise (laptop builds) swu_ipc_compat.h provides the same few calls
 * for the same socket protocol (PROGRESS_API 2.0, SWUpdate 2025.05). */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "swu.h"
#include "job.h"

#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifdef USE_LIBSWUPDATE
#include <progress_ipc.h>
#else
#include "swu_ipc_compat.h"
#endif

static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static swu_state st;
static char sock_path[256];
static char swlog[8192];
static size_t swlog_len;

/* Called with mu held */
static void swlog_add(const char *line)
{
	size_t n = strlen(line);
	if (n + 2 > sizeof(swlog))
		return;
	if (swlog_len + n + 2 > sizeof(swlog)) {	/* drop the older half */
		char *nl = memchr(swlog + swlog_len / 2, '\n', swlog_len / 2);
		size_t drop = nl ? (size_t)(nl - swlog) + 1 : swlog_len;
		memmove(swlog, swlog + drop, swlog_len - drop);
		swlog_len -= drop;
	}
	memcpy(swlog + swlog_len, line, n);
	swlog_len += n;
	swlog[swlog_len++] = '\n';
	swlog[swlog_len] = 0;
}

void swu_log_copy(char *buf, size_t cap)
{
	pthread_mutex_lock(&mu);
	snprintf(buf, cap, "%s", swlog);
	pthread_mutex_unlock(&mu);
}

const char *swu_status_name(swu_status s)
{
	static const char *n[] = { "idle", "starting", "installing", "success",
		"failed", "receiving", "done", "subprocess", "progress" };
	return (unsigned)s < sizeof(n) / sizeof(n[0]) ? n[s] : "?";
}

static void apply(swu_status status, swu_source src, unsigned nsteps,
		  unsigned cur_step, unsigned cur_percent, unsigned dwl_percent,
		  const char *image, const char *handler, const char *info,
		  unsigned infolen)
{
	pthread_mutex_lock(&mu);
	if (status != SWU_PROGRESS) {
		st.status = status;
		st.source = src;
	}
	st.nsteps = nsteps;
	st.cur_step = cur_step;
	st.cur_percent = cur_percent;
	st.dwl_percent = dwl_percent;
	if (image && *image)
		snprintf(st.image, sizeof(st.image), "%s", image);
	if (handler)
		snprintf(st.handler, sizeof(st.handler), "%s", handler);
	if (info && infolen) {
		unsigned n = infolen < sizeof(st.info) - 1 ? infolen : sizeof(st.info) - 1;
		memcpy(st.info, info, n);
		st.info[n] = 0;
		st.info_seq++;
	}
	if (status == SWU_START) {
		swlog_len = 0;
		swlog[0] = 0;
	}
	char line[400];
	if (status == SWU_PROGRESS || (info && infolen)) {
		if (info && infolen) {
			snprintf(line, sizeof(line), "%s", st.info);
			swlog_add(line);
		}
	}
	if (status != SWU_PROGRESS && (status != st.last_logged || cur_step != st.last_step)) {
		if (nsteps)
			snprintf(line, sizeof(line), "%s: step %u/%u %s", swu_status_name(status),
				 cur_step, nsteps, image ? image : "");
		else
			snprintf(line, sizeof(line), "%s", swu_status_name(status));
		swlog_add(line);
		st.last_logged = status;
		st.last_step = cur_step;
	}
	switch (status) {
	case SWU_START:
		st.active = true;
		st.overall = 0;
		st.image[0] = 0;
		break;
	case SWU_DOWNLOAD:
	case SWU_RUN:
	case SWU_SUBPROCESS:
		st.active = true;
		break;
	case SWU_SUCCESS:
		st.overall = 100;
		st.active = false;
		st.result = status;
		st.result_seq++;
		break;
	case SWU_FAILURE:
		st.active = false;
		st.result = status;
		st.result_seq++;
		break;
	case SWU_DONE:
	case SWU_IDLE:
		st.active = false;
		break;
	default:
		break;
	}
	if (status == SWU_DOWNLOAD && !nsteps)
		st.overall = dwl_percent / 2;	/* upload: first half of the bar */
	else if (nsteps && cur_step)
		st.overall = (int)(((cur_step - 1) * 100 + cur_percent) / nsteps);
	if (st.overall > 100)
		st.overall = 100;
	st.seq++;
	pthread_mutex_unlock(&mu);
}

void swu_inject(swu_status status, swu_source src, unsigned nsteps,
		unsigned cur_step, unsigned cur_percent, const char *image,
		const char *info)
{
	apply(status, src, nsteps, cur_step, cur_percent, 0, image, "raw",
	      info, info ? (unsigned)strlen(info) : 0);
}

static void *thread(void *arg)
{
	(void)arg;
	bool said = false;
	for (;;) {
		struct stat sb;
		if (stat(sock_path, &sb) || !S_ISSOCK(sb.st_mode)) {
			sleep(1);
			continue;
		}
		int fd = progress_ipc_connect_with_path(sock_path, false);
		if (fd < 0) {	/* stale socket, daemon gone: don't spin */
			sleep(5);
			continue;
		}
		pthread_mutex_lock(&mu);
		st.connected = true;
		st.seq++;
		pthread_mutex_unlock(&mu);
		if (!said)
			slog("SWUpdate progress: connected (%s)", sock_path);
		said = true;
		struct progress_msg msg;
		while (fd >= 0) {
			memset(&msg, 0, sizeof(msg));
			int r = progress_ipc_receive(&fd, &msg);
			if (r == -EBADMSG) {
				slog("SWUpdate progress: API version mismatch (%#x)",
				     msg.apiversion);
				if (fd >= 0)
					close(fd);
				sleep(30);
				break;
			}
			if (r <= 0)
				continue;	/* fd set to -1 on close */
			unsigned il = msg.infolen < sizeof(msg.info) ? msg.infolen : 0;
			msg.cur_image[sizeof(msg.cur_image) - 1] = 0;
			msg.hnd_name[sizeof(msg.hnd_name) - 1] = 0;
			apply((swu_status)msg.status, (swu_source)msg.source,
			      msg.nsteps, msg.cur_step, msg.cur_percent,
			      msg.dwl_percent, msg.cur_image, msg.hnd_name,
			      msg.info, il);
			if (msg.status != PROGRESS)
				slog("SWUpdate: %s step %u/%u %u%% %s",
				     swu_status_name((swu_status)msg.status),
				     msg.cur_step, msg.nsteps, msg.cur_percent,
				     msg.cur_image);
			if (il)
				slog("SWUpdate: %.*s", (int)il, msg.info);
		}
		pthread_mutex_lock(&mu);
		st.connected = false;
		st.seq++;
		pthread_mutex_unlock(&mu);
		sleep(1);
	}
	return NULL;
}

void swu_start(const char *socket_path)
{
	snprintf(sock_path, sizeof(sock_path), "%s", socket_path);
	pthread_t th;
	pthread_attr_t a;
	pthread_attr_init(&a);
	pthread_attr_setdetachstate(&a, PTHREAD_CREATE_DETACHED);
	pthread_create(&th, &a, thread, NULL);
	pthread_attr_destroy(&a);
}

void swu_get(swu_state *s)
{
	pthread_mutex_lock(&mu);
	*s = st;
	pthread_mutex_unlock(&mu);
}
