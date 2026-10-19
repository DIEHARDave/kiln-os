/* Stand-in for SWUpdate's progress client library when libswupdate isn't
 * available (laptop builds): the same calls and wire format as
 * include/progress_ipc.h of SWUpdate 2025.05 (progress API 2.0.0;
 * progress_ipc.h and ipc/progress_ipc.c are LGPL-2.1-or-later, Siemens AG /
 * Stefano Babic). Only what swu.c uses. The message is the raw C struct,
 * so this must be built with the same ABI as the daemon. */
#ifndef RUI_SWU_IPC_COMPAT_H
#define RUI_SWU_IPC_COMPAT_H

#include <errno.h>
#include <poll.h>
#include <stdbool.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define PRINFOSIZE 2048
#define PROGRESS_API_MAJOR 2
#define PROGRESS_API_MINOR 0
#define PROGRESS_API_PATCH 0
#define PROGRESS_API_VERSION ((PROGRESS_API_MAJOR & 0xFFFF) << 16 | \
			      (PROGRESS_API_MINOR & 0xFF) << 8 | \
			      (PROGRESS_API_PATCH & 0xFF))
#define PROGRESS_CONNECT_ACK_MAGIC "ACK"

typedef enum { IDLE, START, RUN, SUCCESS, FAILURE, DOWNLOAD, DONE,
	       SUBPROCESS, PROGRESS } RECOVERY_STATUS;
typedef enum { SOURCE_UNKNOWN, SOURCE_WEBSERVER, SOURCE_SURICATTA,
	       SOURCE_DOWNLOADER, SOURCE_LOCAL,
	       SOURCE_CHUNKS_DOWNLOADER } sourcetype;

struct progress_msg {
	unsigned int apiversion;
	RECOVERY_STATUS status;
	unsigned int dwl_percent;
	unsigned long long dwl_bytes;
	unsigned int nsteps;
	unsigned int cur_step;
	unsigned int cur_percent;
	char cur_image[256];
	char hnd_name[64];
	sourcetype source;
	unsigned int infolen;
	char info[PRINFOSIZE];
};

struct progress_connect_ack {
	unsigned int apiversion;
	char magic[4];
};

static inline int progress_ipc_connect_with_path(const char *path, bool reconnect)
{
	(void)reconnect;
	struct sockaddr_un sa;
	int fd = socket(AF_LOCAL, SOCK_STREAM | SOCK_CLOEXEC, 0);
	if (fd < 0)
		return -1;
	memset(&sa, 0, sizeof(sa));
	sa.sun_family = AF_LOCAL;
	size_t pl = strlen(path);
	if (pl >= sizeof(sa.sun_path)) {
		close(fd);
		return -1;
	}
	memcpy(sa.sun_path, path, pl + 1);
	if (connect(fd, (struct sockaddr *)&sa, sizeof(sa))) {
		close(fd);
		return -1;
	}
	/* The daemon answers with an ACK carrying its API version */
	struct progress_connect_ack ack;
	size_t got = 0;
	while (got < sizeof(ack)) {
		struct pollfd p = { .fd = fd, .events = POLLIN };
		if (poll(&p, 1, 5000) <= 0)
			break;
		ssize_t n = read(fd, (char *)&ack + got, sizeof(ack) - got);
		if (n <= 0)
			break;
		got += n;
	}
	if (got != sizeof(ack) || ((ack.apiversion >> 16) & 0xFFFF) != PROGRESS_API_MAJOR ||
	    strcmp(ack.magic, PROGRESS_CONNECT_ACK_MAGIC)) {
		close(fd);
		return -1;
	}
	return fd;
}

static inline int progress_ipc_receive(int *connfd, struct progress_msg *msg)
{
	ssize_t ret = read(*connfd, msg, sizeof(*msg));
	if (ret == -1 && (errno == EAGAIN || errno == EINTR))
		return 0;
	if (ret > (ssize_t)sizeof(msg->apiversion) && msg->apiversion != PROGRESS_API_VERSION)
		return -EBADMSG;
	if (ret != (ssize_t)sizeof(*msg)) {
		close(*connfd);
		*connfd = -1;
		return -1;
	}
	return (int)ret;
}

#endif
