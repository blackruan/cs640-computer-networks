#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <netdb.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <math.h>

#define MIN(a,b) (((a)<(b))?(a):(b))
// max length of payload
#define MAXLENGTH 51*1024

int port, num, length, echo;
double rate;
uint32_t seq_no;
int sockfd; 

struct sockaddr_in blter_addr;
struct sockaddr_in bltee_addr;

void usage() {
    fprintf(stderr, "Usage: blaster -s <hostname> -p <port> -r <rate> -n <num> "  
                "-q <seq_no> -l <length> -c <echo>\n");
    exit(1);
}

void *recv_echo() {
    char packet[MAXLENGTH];
    int size;
    char type;
    uint32_t sequence;
    for(;;) {
        if((size = recvfrom(sockfd, packet, MAXLENGTH, 0, NULL, NULL)) <= 0) { 
            printf("recvfrom error\n");
            continue;
        }
        memcpy(&type, packet, 1);
        //printf("type: %c\n",type);
        if(type == 'C') {
            memcpy(&sequence, &packet[1], 4);
            printf("Received ECHO packet:\nseq_no=%u, first 4 bytes: %c%c%c%c\n",
                    ntohl(sequence), packet[9], packet[10], packet[11],
                    packet[12]);
        }
    }
}

int main(int argc, char *argv[]) {
    char *hostname;

    if(argc != 15) {
        usage();
    }

    int c;
    while((c = getopt(argc, argv, "s:p:r:n:q:l:c:")) != -1) {
        switch(c) {
            case 's':
                hostname = strdup(optarg);
                break;
            case 'p':
                port = atoi(optarg);
                if(port <= 1024 || port >= 65536) {
                    fprintf(stderr, "port num out of range\n");
                    exit(1);
                }
                break;
            case 'r':
                rate = strtod(optarg, NULL);
                if(rate <= 0) {
                    fprintf(stderr, "invalid rate\n");
                    exit(1);
                }
                break;
            case 'n':
                num = atoi(optarg);
                if(num <= 0) {
                    fprintf(stderr, "invalid num\n");
                    exit(1);
                }
                break;
            case 'q':
                seq_no = strtoul(optarg, NULL, 10);
                break;
            case 'l':
                length = atoi(optarg);
                if(length < 0 || length >= 50*1024) {
                    fprintf(stderr, "length out of range\n");
                    exit(1);
                }
                break;
            case 'c':
                echo = atoi(optarg);
                if(!(echo == 0 || echo == 1)) {
                    fprintf(stderr, "echo argument: 1 or 0\n");
                    exit(1);
                }
                break;
            default:
                usage();
        }
    }
    
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("cannot create socket");
        exit(1);
    }
    struct hostent *host = gethostbyname(hostname);
    if(host == NULL) {
        fprintf(stderr, "cannot get host address\n");
        exit(1);
    }

    memset((char *)&blter_addr, 0, sizeof(blter_addr));
    blter_addr.sin_family = AF_INET;
    blter_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    blter_addr.sin_port = htons(0);

    if(bind(sockfd, (struct sockaddr *)&blter_addr, sizeof(blter_addr)) < 0) {
        perror("bind failed");
        exit(1);
    }

    memset((char *)&bltee_addr, 0, sizeof(bltee_addr));
    bltee_addr.sin_family = AF_INET;
    bltee_addr.sin_port = htons(port);
    memcpy(&(bltee_addr.sin_addr), host->h_addr, host->h_length);

    // size of datagram in bytes
    int size = length + 9;
    char pkt_type = 'D';
    uint32_t sequence = htonl(seq_no);
    uint32_t l = htonl(length);

    char *datagram = (char*)malloc(size * sizeof(char));
    memset(datagram, 0, size);
    memcpy(datagram, &pkt_type, 1);
    memcpy(&datagram[1], &sequence, 4);
    memcpy(&datagram[5], &l, 4);

///*
    // inject msg into datagram
    char* msg= "The_ability_to_destroy_a_planet_is_insignificant_next_to_the_power_of_the_Force";
    int k;
    int span = MIN(length, (int) strlen(msg));
    memcpy(&datagram[9], msg, span);
    /*
    for (k= 0; k < span; k++) {
      datagram[9+k]= msg[k];
    }
    */
    //printf("original buffer: %s\n", datagram); 
    //printf("data: %c%c%c%c\n",datagram[9],datagram[10],datagram[11],datagram[12]);
//*/

    double value = 1 / rate;
    double fractional = fmod(value, 1);
    double integral = value - fractional;
    // in microseconds
    int interval = fractional * 1000000; 

    if(echo == 1) {
        pthread_t *child = (pthread_t *)malloc(sizeof(pthread_t));
        pthread_create(child, NULL, recv_echo, NULL);
    }
    
    // send DATA packet
    int i;
    for(i = 0; i < num; i++) {
        if(sendto(sockfd, datagram, size, 0, (struct sockaddr *)&bltee_addr, 
                sizeof(bltee_addr)) < 0) {
            printf("sendto error\n");
            continue;
        }
        printf("Sending DATA packet:\nseq_no=%u, first 4 bytes: %c%c%c%c\n",
                ntohl(sequence), datagram[9], datagram[10], datagram[11],
                datagram[12]);
        // cannot add on sequence (in network byte order) directly
        seq_no += length;
        sequence = htonl(seq_no);
        memcpy(&datagram[1], &sequence, 4);
        sleep(integral);
        //printf("integral: %f\n", integral);
        usleep(interval);
        //printf("interval: %d\n", interval);
    }


    // send END packet
    pkt_type = 'E';
    memcpy(datagram, &pkt_type, 1);
    if(sendto(sockfd, datagram, size, 0, (struct sockaddr *)&bltee_addr, 
                sizeof(bltee_addr)) < 0) {
        printf("sendto error\n");
        exit(1);
    }
    printf("Sending END packet:\nseq_no=%u, first 4 bytes: %c%c%c%c\n", 
            ntohl(sequence), datagram[9], datagram[10], datagram[11],
            datagram[12]);

    //pthread_join(*child, NULL);
    
    free(datagram);
    //close(sockfd);
    return 0;
}
