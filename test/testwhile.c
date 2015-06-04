#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>

void sig_handler(int signo)
{
	if (signo == SIGINT)
	    printf("received SIGINT\n");
	exit(0);
}
int main()
{
	while(32)
	{
		if (signal(SIGINT, sig_handler) == SIG_ERR)
			printf("\ncan't catch SIGINT\n");
		printf("toto\n");
		sleep(2);
	}
	return (0);
}