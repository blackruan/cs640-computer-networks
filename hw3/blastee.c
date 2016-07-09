#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/in.h>
#include <netinet/udp.h>

#define MAXBUF 51*1024

// print first 4 bytes of payload
void print_payload(char* msg,int length) {
  int j;
  printf("Data (first 4 bytes): ");
  for (j=9; j < 9+length; j++) {
    printf("%c",msg[j]);
  }
  printf("\n");
}

// print summary statistics
void print_stat(int num_pkt, int num_bytes, 
                double avg_pkt, double avg_bytes, double time_duration) {
  printf("Summary Statistics:\n--------------------\n");
  // print total packets received
  printf("total packets received= %d\n",num_pkt);
  // print total bytes received
  printf("total bytes received= %d\n",num_bytes);
  // print average packets/s
  printf("average packets/s: %.4f\n",avg_pkt);
  // print average bytes/s
  printf("average bytes/s: %.4f\n",avg_bytes);
  // print duration of test
  printf("duration of test: %.6fs\n",time_duration);
}

// main function
int main (int argc, char** argv) {

  // declare variables
  char* usage= "usage: blastee -p <port> -c <echo>\n";
  int c, err= 0;
  int pflag= 0, cflag= 0;
  int portnum, echoflag;
  extern char* optarg;
  extern int optind, optopt;

  // check for options
  while ((c= getopt(argc, argv, "p:c:")) != -1) {
    switch(c) {
      case 'p':
        pflag= 1;
        portnum= atoi(optarg);
        break;
      case 'c':
        cflag= 1;
        echoflag= atoi(optarg);
        break;
      case '?':
        err= 1;
        break;
    }
  }

  // exit if invalid option
  if (err) { 
    fprintf(stderr, "%s",usage); 
    exit(1); 
  }
  // exit if invalid port or echo type
  if (!(portnum > 1024 && portnum < 65536) || !(echoflag >= 0 && echoflag < 2)) {
    printf("your input: <port>= %d, <echo>= %d\n",portnum,echoflag);
    fprintf(stderr,"please enter: <port>= (1024,65535), <echo>= {0,1}\n");
    exit(1);
  } 

  // print out parameters
  printf("port: %d\n",portnum);
  printf("echo: %d\n",echoflag);

  // create variables for receiving datagram
  int socket_udp;
  struct sockaddr_in client_addr, server_addr;  
  char bufmsg[MAXBUF];

  // create socket
  printf("create socket\n");
  socket_udp= socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
  printf("socket status: %d\n",socket_udp);
  if (socket_udp == -1) {
    printf("Could not create socket");
  }

  // construct the server address
  bzero((char *) &server_addr, sizeof(server_addr));
  server_addr.sin_family = AF_INET;
  server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
  server_addr.sin_port = htons(portnum);

  // bind the socket
  if (bind(socket_udp,(struct sockaddr*) &server_addr,sizeof(server_addr)) < 0) {
    fprintf(stderr,"error: cannot bind\nexiting...\n");
    exit(1);
  }

  // additional variable in recvfrom
  struct timeval time_start, time_first, time_elapsed;
  struct timeval time_first_diff, time_diff, time_end_diff;
  struct timeval timeout;
  timeout.tv_sec= 5;
  timeout.tv_usec= 0;
  int packet, num_pkt= 0, num_bytes= 0;
  double avg_pkt= 0.0, avg_bytes= 0.0;
  socklen_t len= sizeof(client_addr);

  //start timing  
  gettimeofday(&time_start, NULL);
  gettimeofday(&time_first, NULL);

  // receive datagram
  while (1) {
    
    // set buffer message to zero
    bzero(bufmsg,MAXBUF);

    if (setsockopt(socket_udp,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout)) < 0) {
      fprintf(stderr,"error: setsockopt\n");
      exit(1);
    }

    // try to receive packet
    packet= recvfrom(socket_udp,bufmsg,MAXBUF,0,(struct sockaddr*)&client_addr,&len);
    
    // check if we can receive?
    if (packet < 0) {
      // elapsed time
      gettimeofday(&time_elapsed, NULL);
      timersub(&time_elapsed,&time_first,&time_diff);
      timersub(&time_elapsed,&time_start,&time_end_diff);
      double elapsed= (double)(time_diff.tv_sec*1000000 + (int)time_diff.tv_usec)/1000000;
      double end_timeout= (double)(time_end_diff.tv_sec*1000000 + (int)time_end_diff.tv_usec)/1000000;
      printf("Timeout at %.6fs\n",elapsed);
      // print statistics
      avg_pkt= (double)num_pkt/elapsed;
      avg_bytes= (double)num_bytes/elapsed;
      print_stat(num_pkt,num_bytes,avg_pkt,avg_bytes,elapsed);
      printf("total online time: %.6fs\n",end_timeout);
      break;
//      fprintf(stderr,"error: cannot receive data...\nexiting...\n");
//      exit(1);
    } else {
      
      // first time receive paket timestamp
      if (num_pkt == 0) {
        gettimeofday(&time_first, NULL);
        timersub(&time_first,&time_start,&time_first_diff);
        double first_elapsed= (double)(time_first_diff.tv_sec*1000000 + (int)time_first_diff.tv_usec)/1000000;
        printf("first packet received at %.6fs\n",first_elapsed);
        printf("start timing...\n");
      }

      // elapsed time
      gettimeofday(&time_elapsed, NULL);
      timersub(&time_elapsed,&time_first,&time_diff);
      double elapsed= (double)(time_diff.tv_sec*1000000 + (int)time_diff.tv_usec)/1000000;

      // print datatype
      printf("Receiving packet... type: %c\n",bufmsg[0]);

      if (bufmsg[0] == 'D') {
        // print where datagram came from
        printf("received datagram from %s at port %d\n",
               inet_ntoa(client_addr.sin_addr),ntohs(server_addr.sin_port));
        // print seq num
        uint32_t sequence;
        memcpy(&sequence,&bufmsg[1], 4);
        printf("seq_no= %u, ",ntohl(sequence));
        // print bytes of datagram
        uint32_t data_length;
        memcpy(&data_length,&bufmsg[5], 4);
//        printf("received %u bytes of data, ",ntohl(data_length));
        printf("received %d bytes of data\n",packet);
        // print received time
        printf("time received at %.6fs, or %.4fms\n",elapsed,elapsed*1000);
        // print first 4 bytes of payload
        print_payload(bufmsg,4);
        // increment number of packet received
        num_pkt++;
//        num_bytes+= (int)ntohl(data_length);
        num_bytes+= packet;
        // echo if echoflag= 1
        if (echoflag == 1) {
          char pkt_type= 'C';
          memcpy(bufmsg, &pkt_type, 1);
          sendto(socket_udp,bufmsg,packet,0,(struct sockaddr*)&client_addr,len);
        }
      }
      else if (bufmsg[0]== 'E') {
        
        // elapsed time
        gettimeofday(&time_elapsed, NULL);
        timersub(&time_elapsed,&time_first,&time_diff);
        timersub(&time_elapsed,&time_start,&time_end_diff);
        double time_duration= (double)(time_diff.tv_sec*1000000 + (int)time_diff.tv_usec)/1000000;
        double end_time= (double)(time_end_diff.tv_sec*1000000 + (int)time_end_diff.tv_usec)/1000000;

        // print statistics
        avg_pkt= (double)num_pkt/time_duration;
        avg_bytes= (double)num_bytes/time_duration;
        print_stat(num_pkt,num_bytes,avg_pkt,avg_bytes,time_duration);  
        printf("total online time: %.6fs\n",end_time);

        // reset all statistics variables
/*
        num_pkt= 0;
        num_bytes= 0;
        avg_pkt= 0.0;
        avg_bytes= 0.0;
*/
        printf("DONE !!!\n");
        break;
      }
      else {
        continue;
      }
    }   
  }
  close(socket_udp);
  return 0;
}
