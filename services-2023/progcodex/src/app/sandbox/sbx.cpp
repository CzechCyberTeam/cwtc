#include <cstdio>
#include <iostream>
#include <fstream>
#include <sys/mman.h>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
#include <sys/prctl.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <grp.h>
#include <sys/sendfile.h>

// Define the maximum allowed execution time in seconds
const int MAX_EXECUTION_TIME = 3;

// Function to load shellcode from a file
char* loadShellcodeFromFile(const char* filename, size_t& shellcodeSize) {
  std::ifstream file(filename, std::ios::binary | std::ios::ate);
  if (!file) {
    std::cerr << "Failed to open shellcode file." << std::endl;
    return nullptr;
  }

  shellcodeSize = file.tellg();
  char* shellcode = new char[shellcodeSize];

  file.seekg(0, std::ios::beg);
  file.read(shellcode, shellcodeSize);
  file.close();

  return shellcode;
}

void timeoutHandler(int signum) {
    std::cerr << "Timeout occurred. Terminating the program. #SIG: " << signum << std::endl;
    exit(EXIT_FAILURE);
}

// Function to set up seccomp filter to blacklist syscalls
void setSeccompFilter() {
  struct sock_filter filter[] = {
      BPF_STMT(BPF_LD | BPF_W | BPF_ABS, (offsetof(struct seccomp_data, nr))),

      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_execve, 0, 1),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),

      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_fork, 0, 1),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),

      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_vfork, 0, 1),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),

      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_kill, 0, 1),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),

      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
  };

  struct sock_fprog prog{};
  prog.len = (unsigned short)(sizeof(filter) / sizeof(filter[0]));
  prog.filter = filter;

  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == -1) {
    std::cerr << "Failed to set PR_SET_NO_NEW_PRIVS." << std::endl;
    exit(EXIT_FAILURE);
  }

  if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog) == -1) {
    std::cerr << "Failed to set PR_SET_SECCOMP." << std::endl;
    exit(EXIT_FAILURE);
  }
}

int main(int argc, char* argv[]) {
  if (argc != 2 && argc != 3) {
    std::cerr << "Usage: " << argv[0] << " <shellcode_file_path> (<inputfile>)" << std::endl;
    return EXIT_FAILURE;
  }

  const char* shellcodeFile = argv[1];
  size_t shellcodeSize;
  char* shellcode = loadShellcodeFromFile(shellcodeFile, shellcodeSize);
  if (!shellcode) {
    return EXIT_FAILURE;
  }

  // Allocate memory for the shellcode
  void* executableMemory = mmap((void*) 0x1337, shellcodeSize, PROT_READ | PROT_WRITE | PROT_EXEC,
                                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (executableMemory == MAP_FAILED) {
    std::cerr << "Failed to allocate memory." << std::endl;
    return EXIT_FAILURE;
  }

  // Copy the shellcode to the allocated memory
  memcpy(executableMemory, shellcode, shellcodeSize);

  // Set the resource limits for execution time
  struct rlimit timeLimit{};
  timeLimit.rlim_cur = MAX_EXECUTION_TIME;
  timeLimit.rlim_max = MAX_EXECUTION_TIME;
  if (setrlimit(RLIMIT_CPU, &timeLimit) == -1) {
    std::cerr << "Failed to set CPU time limit." << std::endl;
    return EXIT_FAILURE;
  }

  signal(SIGALRM, timeoutHandler);
  alarm(MAX_EXECUTION_TIME);

  int input_file_selection;
  if (argc != 3) {
    input_file_selection = 0;
  } else {
    input_file_selection = atoi(argv[2]);
  }

  int input;
  switch (input_file_selection) {
    default:
    case 0:
      input = open("/app/sandbox/inputs/graph.txt", O_RDONLY);
      break;
    case 1:
      input = open("/app/sandbox/inputs/life.txt", O_RDONLY);
      break;
    // TODO: Add more inputs
  }

  printf("Input file: %d\n", input);

  int dest = open("/dev/stdout", O_WRONLY, 0644);
  printf("Output file: %d\n", dest);
  
  // Set up seccomp syscall filter
  setSeccompFilter();

  // Execute the shellcode
  typedef void (*ShellcodeFunction)();
  ShellcodeFunction function = reinterpret_cast<ShellcodeFunction>(executableMemory);
  function();

  // Free the allocated memory
  munmap(executableMemory, shellcodeSize);

  return EXIT_SUCCESS;
}
