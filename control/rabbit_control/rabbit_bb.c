#include <sys/socket.h>       /*  socket definitions        */
#include <sys/types.h>        /*  socket types              */
#include <arpa/inet.h>        /*  inet (3) funtions         */
#include <unistd.h>           /*  misc. UNIX functions      */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <netinet/in.h>

#define PORT 3023
#define USERAGENT "ApOgEE MinGW Socket Client 1.0"

void calibrate(int channel);
void load_file(void);

char *build_get_query(char *, char *);
int i;
int client_socket;
int iplen = 15; //XXX.XXX.XXX.XXX
struct sockaddr_in *remote;
int tmpres;
char *argument;
int j;
char buf[512] = { 0 };
int nleft = 512;
int ipos = 0;
int ndata = 0;
char str1[] = "start";
char str2[] = "stop";
char str3[] = "hold";
FILE *fp;
char *ip;
char *filename;
char *result = NULL;
char delims[] = " ";
int quit, sent, sentcount;

int main(int argc, char *argv[]) {

	printf("Socket client example\n");

	quit = 0;
// create tcp socket

	client_socket = socket(PF_INET, SOCK_DGRAM, IPPROTO_TCP);
	if (client_socket < 0) {
		printf("client_socket = %d\n", client_socket);
		perror("Can't create TCP socket\n");
		exit(1);
	}

	ip = (char *) malloc(iplen + 1);
	memset(ip, 0, iplen + 1);

	//ip = "131.142.12.62";
	ip = "192.168.25.7";
	printf("The IP: %s\n", ip);

// setup remote socket
	remote = (struct sockaddr_in *) malloc(sizeof(struct sockaddr_in *));
	remote->sin_family = AF_INET;
	printf("s_addr:%lu\n", remote->sin_addr.s_addr);
	remote->sin_addr.s_addr = inet_addr(ip);
	remote->sin_port = htons(PORT);
	printf("s_addr:%lu\n", remote->sin_addr.s_addr);



    printf("Remote socket set\n");
// connect socket
	if (connect(client_socket, (struct sockaddr *) remote,
		    sizeof(struct sockaddr)) /*== SO_ERROR*/) {
		close(client_socket);
		perror("Could not connect");
		exit(1);
	}

	printf("the first argument is %s\n", argv[1]);
	argument = argv[1];

	if (argument == NULL){
		argument = "999";
	}


//Send the query to the server
        printf("sending query\n");
	sent = 0;
	while (sent < strlen(argument)) {
                printf("in while loop\n");
		tmpres = send(client_socket, argument, strlen(argument), 0);
                printf("port tempres\n");
		if (tmpres == -1) {
			perror("Can't send query");
			exit(1);
		}
		sent += tmpres;
		printf("sent some stuff\n");
	}
	for (j = 0; j < 20000; j++)
		;
	printf("\n");

	tmpres = 1;

	tmpres = send(client_socket, argument, strlen(argument), 0);

	do {
		ndata = recv(client_socket, &buf[ipos], nleft, 0);
		nleft -= ndata;
		ipos += ndata;

	} while (nleft > 0); 

	printf("%s\n", buf);

        printf("query sent\n");
	free(argument);
	free(remote);
	close(client_socket);

	printf("Program end");

	return 0;
}

char *build_get_query(char *host, char *page) {
	char *query;
	char *getpage = page;
	char *tpl = "GET /%s HTTP/1.0\r\nHost: %s\r\nUser-Agent: %s\r\n\r\n";
	if (getpage[0] == '/') {
		getpage = getpage + 1;
		fprintf(stderr, "Removing leading \"/\", converting %s to %s\n", page,
				getpage);
	}
// -5 is to consider the %s %s %s in tpl and the ending \0
	query = (char *) malloc(
			strlen(host) + strlen(getpage) + strlen(USERAGENT) + strlen(tpl)
					- 5);
	sprintf(query, tpl, getpage, host, USERAGENT);
	return query;
}

void calibrate(int channel) {

	char *lag_num;
	//   lag_num = "0";
	sprintf(lag_num, "%d", channel);
	//  itoa(channel, lag_num, 10);
	printf("the lag is number %s\n", lag_num);

	sent = 0;
	while (sent < strlen(argument)) {
		tmpres = send(client_socket, lag_num, strlen(lag_num), 0);
		if (tmpres == -1) {
			perror("Can't send query");
			exit(1);
		}
		sent += tmpres;
	}

	for (j = 0; j < 20000; j++)
		;
	printf("\n");

	tmpres = 1;

	do {
		ndata = recv(client_socket, &buf[ipos], nleft, 0);
		nleft -= ndata;
		ipos += ndata;

	} while (nleft > 0);

}
void load_file(void) {

	filename = "cal_matrix.dat";
//	char delims[] = " ";
	fp = fopen(filename, "r");
//	char *result = NULL;

	if (fp != NULL) {
		char line[150]; /* or other suitable maximum line size */
		while (fgets(line, sizeof(line), fp) != NULL) /* read a line */
		{
			result = strtok(line, delims);
			while (result != NULL) {
				if (!isspace(result[0])) {
					printf("result is %s\n", result);
					sentcount = 0;
					while (sentcount < strlen(result)) {
						tmpres = send(client_socket, result, strlen(result), 0);
						if (tmpres == -1) {
							perror("Can't send query");
							exit(1);
						}
						sentcount += tmpres;
					}

				}
				result = strtok(NULL, delims);
			}

			//fputs(line, stdout); /* write the line */
		}
		fclose(fp);
		quit = 1;
	}

//	fclose(fp);
}
