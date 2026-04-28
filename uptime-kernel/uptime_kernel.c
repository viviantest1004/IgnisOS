/*
 * IgnisOS — Uptime Kernel v1.0.0
 * A custom boot-time shell environment for IgnisOS
 * License: MIT
 *
 * Commands:
 *   ls [path]        List files/directories
 *   cd <path>        Change directory
 *   pwd              Print working directory
 *   mkdir <dir>      Create directory
 *   rmdir <dir>      Remove empty directory
 *   rm <file>        Remove file
 *   touch <file>     Create empty file
 *   cat <file>       Print file contents
 *   cp <src> <dst>   Copy file
 *   mv <src> <dst>   Move/rename file
 *   calc <expr>      Calculator (+ - * /)
 *   uptime           Show system uptime
 *   uname            Show system info
 *   clear            Clear screen
 *   help             Show this help
 *   exit             Exit Uptime Kernel → boot IgnisOS
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#ifdef __linux__
#  include <sys/sysinfo.h>
#else
   /* macOS fallback — build target은 Linux ARM64 */
#  include <sys/sysctl.h>
#  include <mach/mach.h>
#  include <mach/mach_host.h>
#endif
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <signal.h>
#include <termios.h>

/* ── ANSI 색상 ─────────────────────────────────────── */
#define RED     "\033[1;31m"
#define GREEN   "\033[1;32m"
#define YELLOW  "\033[1;33m"
#define BLUE    "\033[1;34m"
#define MAGENTA "\033[1;35m"
#define CYAN    "\033[1;36m"
#define WHITE   "\033[1;37m"
#define ORANGE  "\033[38;5;208m"
#define DIM     "\033[2m"
#define BOLD    "\033[1m"
#define RESET   "\033[0m"

#define VERSION  "1.0.0"
#define HOSTNAME "ignis"
#define MAX_CMD  1024
#define MAX_ARGS 64
#define MAX_PATH 4096

static char cwd[MAX_PATH];

/* ── 배너 ──────────────────────────────────────────── */
static void print_banner(void) {
    printf("\033[2J\033[H"); /* clear */
    printf(ORANGE
        "  ██╗ ██████╗ ███╗   ██╗██╗███████╗ ██████╗ ███████╗\n"
        "  ██║██╔════╝ ████╗  ██║██║██╔════╝██╔═══██╗██╔════╝\n"
        "  ██║██║  ███╗██╔██╗ ██║██║███████╗██║   ██║███████╗\n"
        "  ██║██║   ██║██║╚██╗██║██║╚════██║██║   ██║╚════██║\n"
        "  ██║╚██████╔╝██║ ╚████║██║███████║╚██████╔╝███████║\n"
        "  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚══════╝ ╚═════╝ ╚══════╝\n"
        RESET);
    printf(DIM "  ─────────────────────────────────────────────────────\n" RESET);
    printf(CYAN "  Uptime Kernel " WHITE "v" VERSION CYAN
           "  ·  ARM64  ·  MIT License\n" RESET);
    printf(DIM "  Type " RESET GREEN "help" RESET DIM
           " for available commands, " RESET RED "exit" RESET
           DIM " to boot IgnisOS desktop\n" RESET);
    printf(DIM "  ─────────────────────────────────────────────────────\n\n" RESET);
}

/* ── 프롬프트 출력 ─────────────────────────────────── */
static void print_prompt(void) {
    getcwd(cwd, sizeof(cwd));
    /* home 디렉토리를 ~로 단축 */
    const char *home = getenv("HOME");
    char display[MAX_PATH];
    if (home && strncmp(cwd, home, strlen(home)) == 0) {
        snprintf(display, sizeof(display), "~%s", cwd + strlen(home));
    } else {
        strncpy(display, cwd, sizeof(display));
    }
    printf(GREEN BOLD "root" RESET DIM "@" RESET
           CYAN BOLD HOSTNAME RESET ":" BLUE "%s" RESET
           MAGENTA " ❯ " RESET, display);
    fflush(stdout);
}

/* ── 문자열 파싱 ───────────────────────────────────── */
static int parse_args(char *line, char **argv) {
    int argc = 0;
    char *p = line;
    while (*p) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        if (*p == '"') {
            p++;
            argv[argc++] = p;
            while (*p && *p != '"') p++;
            if (*p) *p++ = '\0';
        } else {
            argv[argc++] = p;
            while (*p && *p != ' ' && *p != '\t') p++;
            if (*p) *p++ = '\0';
        }
        if (argc >= MAX_ARGS - 1) break;
    }
    argv[argc] = NULL;
    return argc;
}

/* ── ls ────────────────────────────────────────────── */
static void cmd_ls(const char *path) {
    const char *target = path ? path : ".";
    DIR *dir = opendir(target);
    if (!dir) {
        printf(RED "ls: cannot open '%s': %s\n" RESET, target, strerror(errno));
        return;
    }
    struct dirent *entry;
    struct stat st;
    char fullpath[MAX_PATH];
    int count = 0;
    while ((entry = readdir(dir))) {
        if (entry->d_name[0] == '.') continue;
        snprintf(fullpath, sizeof(fullpath), "%s/%s", target, entry->d_name);
        stat(fullpath, &st);
        if (S_ISDIR(st.st_mode))
            printf(BLUE BOLD "%-20s" RESET, entry->d_name);
        else if (st.st_mode & S_IXUSR)
            printf(GREEN "%-20s" RESET, entry->d_name);
        else
            printf("%-20s", entry->d_name);
        if (++count % 4 == 0) printf("\n");
    }
    if (count % 4 != 0) printf("\n");
    if (count == 0) printf(DIM "(empty)\n" RESET);
    closedir(dir);
}

/* ── cat ───────────────────────────────────────────── */
static void cmd_cat(const char *file) {
    if (!file) { printf(RED "cat: missing filename\n" RESET); return; }
    FILE *f = fopen(file, "r");
    if (!f) { printf(RED "cat: %s: %s\n" RESET, file, strerror(errno)); return; }
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0)
        fwrite(buf, 1, n, stdout);
    fclose(f);
    printf("\n");
}

/* ── mkdir ─────────────────────────────────────────── */
static void cmd_mkdir(const char *dir) {
    if (!dir) { printf(RED "mkdir: missing directory name\n" RESET); return; }
    if (mkdir(dir, 0755) != 0)
        printf(RED "mkdir: cannot create '%s': %s\n" RESET, dir, strerror(errno));
    else
        printf(GREEN "Created directory: %s\n" RESET, dir);
}

/* ── touch ─────────────────────────────────────────── */
static void cmd_touch(const char *file) {
    if (!file) { printf(RED "touch: missing filename\n" RESET); return; }
    FILE *f = fopen(file, "a");
    if (!f) { printf(RED "touch: %s: %s\n" RESET, file, strerror(errno)); return; }
    fclose(f);
    printf(GREEN "Touched: %s\n" RESET, file);
}

/* ── rm ────────────────────────────────────────────── */
static void cmd_rm(const char *file) {
    if (!file) { printf(RED "rm: missing filename\n" RESET); return; }
    if (remove(file) != 0)
        printf(RED "rm: cannot remove '%s': %s\n" RESET, file, strerror(errno));
    else
        printf(GREEN "Removed: %s\n" RESET, file);
}

/* ── rmdir ─────────────────────────────────────────── */
static void cmd_rmdir(const char *dir) {
    if (!dir) { printf(RED "rmdir: missing directory name\n" RESET); return; }
    if (rmdir(dir) != 0)
        printf(RED "rmdir: cannot remove '%s': %s\n" RESET, dir, strerror(errno));
    else
        printf(GREEN "Removed directory: %s\n" RESET, dir);
}

/* ── cp ────────────────────────────────────────────── */
static void cmd_cp(const char *src, const char *dst) {
    if (!src || !dst) { printf(RED "cp: usage: cp <src> <dst>\n" RESET); return; }
    FILE *in = fopen(src, "rb");
    if (!in) { printf(RED "cp: %s: %s\n" RESET, src, strerror(errno)); return; }
    FILE *out = fopen(dst, "wb");
    if (!out) { fclose(in); printf(RED "cp: %s: %s\n" RESET, dst, strerror(errno)); return; }
    char buf[8192]; size_t n;
    while ((n = fread(buf, 1, sizeof(buf), in)) > 0) fwrite(buf, 1, n, out);
    fclose(in); fclose(out);
    printf(GREEN "Copied: %s → %s\n" RESET, src, dst);
}

/* ── mv ────────────────────────────────────────────── */
static void cmd_mv(const char *src, const char *dst) {
    if (!src || !dst) { printf(RED "mv: usage: mv <src> <dst>\n" RESET); return; }
    if (rename(src, dst) != 0)
        printf(RED "mv: %s: %s\n" RESET, src, strerror(errno));
    else
        printf(GREEN "Moved: %s → %s\n" RESET, src, dst);
}

/* ── uptime ────────────────────────────────────────── */
static void cmd_uptime(void) {
    time_t now = time(NULL);
    struct tm *tm_now = localtime(&now);
    char timebuf[32];
    strftime(timebuf, sizeof(timebuf), "%H:%M:%S", tm_now);
    printf(CYAN "  System Time : " WHITE "%s\n" RESET, timebuf);

#ifdef __linux__
    struct sysinfo info;
    if (sysinfo(&info) != 0) {
        printf(RED "uptime: failed to get system info\n" RESET); return;
    }
    long total = info.uptime;
    int days  = total / 86400;
    int hours = (total % 86400) / 3600;
    int mins  = (total % 3600)  / 60;
    int secs  = total % 60;
    printf(CYAN "  Uptime      : " WHITE);
    if (days)  printf("%d day%s, ", days, days != 1 ? "s" : "");
    printf("%02d:%02d:%02d\n" RESET, hours, mins, secs);

    double load[3];
    load[0] = info.loads[0] / 65536.0;
    load[1] = info.loads[1] / 65536.0;
    load[2] = info.loads[2] / 65536.0;
    printf(CYAN "  Load Avg    : " WHITE "%.2f  %.2f  %.2f\n" RESET,
           load[0], load[1], load[2]);

    unsigned long total_mb = info.totalram * info.mem_unit / 1024 / 1024;
    unsigned long free_mb  = info.freeram  * info.mem_unit / 1024 / 1024;
    printf(CYAN "  Memory      : " WHITE "%lu MB used / %lu MB total\n" RESET,
           total_mb - free_mb, total_mb);
    printf(CYAN "  Processes   : " WHITE "%d running\n" RESET, info.procs);

#else
    /* macOS fallback */
    int mib[2] = { CTL_KERN, KERN_BOOTTIME };
    struct timeval boottime;
    size_t len = sizeof(boottime);
    if (sysctl(mib, 2, &boottime, &len, NULL, 0) == 0) {
        time_t uptime_sec = now - boottime.tv_sec;
        int days  = uptime_sec / 86400;
        int hours = (uptime_sec % 86400) / 3600;
        int mins  = (uptime_sec % 3600) / 60;
        int secs  = uptime_sec % 60;
        printf(CYAN "  Uptime      : " WHITE);
        if (days) printf("%d day%s, ", days, days != 1 ? "s" : "");
        printf("%02d:%02d:%02d\n" RESET, hours, mins, secs);
    }
    /* memory via mach */
    mach_port_t host = mach_host_self();
    vm_size_t page_size;
    host_page_size(host, &page_size);
    vm_statistics64_data_t vm_stat;
    mach_msg_type_number_t count = HOST_VM_INFO64_COUNT;
    host_statistics64(host, HOST_VM_INFO64, (host_info64_t)&vm_stat, &count);
    unsigned long long free_pages = vm_stat.free_count + vm_stat.inactive_count;
    unsigned long long used_pages = vm_stat.active_count + vm_stat.wire_count;
    printf(CYAN "  Memory      : " WHITE "%llu MB used / —\n" RESET,
           used_pages * page_size / 1024 / 1024);
    (void)free_pages;
#endif
}

/* ── uname ─────────────────────────────────────────── */
static void cmd_uname(void) {
    printf(CYAN "  OS          : " WHITE "IgnisOS 1.0.0 (ARM64)\n" RESET);
    printf(CYAN "  Kernel      : " WHITE "Uptime Kernel v" VERSION "\n" RESET);
    printf(CYAN "  Arch        : " WHITE "aarch64\n" RESET);
    printf(CYAN "  License     : " WHITE "MIT\n" RESET);
}

/* ── 계산기 ────────────────────────────────────────── */

/* 간단한 재귀 하강 파서 */
typedef struct { const char *p; } Parser;

static double parse_expr(Parser *pr);
static double parse_term(Parser *pr);
static double parse_factor(Parser *pr);

static void skip_ws(Parser *pr) {
    while (*pr->p == ' ' || *pr->p == '\t') pr->p++;
}

static double parse_number(Parser *pr) {
    skip_ws(pr);
    char *end;
    double v = strtod(pr->p, &end);
    if (end == pr->p) {
        printf(RED "calc: invalid expression\n" RESET);
        return 0;
    }
    pr->p = end;
    return v;
}

static double parse_factor(Parser *pr) {
    skip_ws(pr);
    if (*pr->p == '(') {
        pr->p++;
        double v = parse_expr(pr);
        skip_ws(pr);
        if (*pr->p == ')') pr->p++;
        return v;
    }
    if (*pr->p == '-') {
        pr->p++;
        return -parse_factor(pr);
    }
    return parse_number(pr);
}

static double parse_term(Parser *pr) {
    double left = parse_factor(pr);
    for (;;) {
        skip_ws(pr);
        char op = *pr->p;
        if (op != '*' && op != '/' && op != '%') break;
        pr->p++;
        double right = parse_factor(pr);
        if (op == '*') left *= right;
        else if (op == '/') {
            if (right == 0) { printf(RED "calc: division by zero\n" RESET); return 0; }
            left /= right;
        } else {
            left = fmod(left, right);
        }
    }
    return left;
}

static double parse_expr(Parser *pr) {
    double left = parse_term(pr);
    for (;;) {
        skip_ws(pr);
        char op = *pr->p;
        if (op != '+' && op != '-') break;
        pr->p++;
        double right = parse_term(pr);
        left = (op == '+') ? left + right : left - right;
    }
    return left;
}

static void cmd_calc(int argc, char **argv) {
    if (argc < 2) {
        printf(RED "calc: usage: calc <expression>\n" RESET);
        printf(DIM "  Examples: calc 2+3   calc 10/4   calc (5+3)*2\n" RESET);
        return;
    }
    /* join all args into one expression */
    char expr[MAX_CMD] = "";
    for (int i = 1; i < argc; i++) {
        strncat(expr, argv[i], sizeof(expr) - strlen(expr) - 1);
    }
    Parser pr = { .p = expr };
    double result = parse_expr(&pr);
    /* 결과가 정수면 정수로 출력 */
    if (result == (long long)result)
        printf(CYAN "  " WHITE "%s " DIM "= " RESET GREEN BOLD "%.0f\n" RESET, expr, result);
    else
        printf(CYAN "  " WHITE "%s " DIM "= " RESET GREEN BOLD "%.10g\n" RESET, expr, result);
}

/* ── help ──────────────────────────────────────────── */
static void cmd_help(void) {
    printf(YELLOW BOLD "\n  IgnisOS Uptime Kernel — 명령어 목록\n\n" RESET);
    printf(CYAN "  파일 관리\n" RESET);
    printf("    %-20s %s\n", "ls [path]",     "파일/폴더 목록");
    printf("    %-20s %s\n", "cd <path>",     "디렉토리 이동");
    printf("    %-20s %s\n", "pwd",           "현재 경로 출력");
    printf("    %-20s %s\n", "mkdir <dir>",   "디렉토리 생성");
    printf("    %-20s %s\n", "rmdir <dir>",   "빈 디렉토리 삭제");
    printf("    %-20s %s\n", "rm <file>",     "파일 삭제");
    printf("    %-20s %s\n", "touch <file>",  "빈 파일 생성");
    printf("    %-20s %s\n", "cat <file>",    "파일 내용 출력");
    printf("    %-20s %s\n", "cp <src> <dst>","파일 복사");
    printf("    %-20s %s\n", "mv <src> <dst>","파일 이동/이름변경");
    printf(CYAN "\n  시스템\n" RESET);
    printf("    %-20s %s\n", "uptime",        "시스템 업타임 및 메모리");
    printf("    %-20s %s\n", "uname",         "시스템 정보");
    printf("    %-20s %s\n", "clear",         "화면 지우기");
    printf("    %-20s %s\n", "help",          "이 도움말");
    printf(CYAN "\n  계산기\n" RESET);
    printf("    %-20s %s\n", "calc <식>",     "사칙연산 계산기 (+ - * / %)");
    printf(DIM   "    예시: calc 2+3  calc 10/4  calc (5+3)*2\n" RESET);
    printf(RED "\n    exit              " RESET "Uptime Kernel 종료 → IgnisOS 부팅\n\n");
}

/* ── 시그널 핸들러 (Ctrl+C 무시) ──────────────────── */
static void sig_handler(int sig) {
    (void)sig;
    printf(YELLOW "\n  [Ctrl+C] 종료하려면 " RED "'exit'" YELLOW " 를 입력하세요\n" RESET);
    print_prompt();
    fflush(stdout);
}

/* ── 메인 루프 ─────────────────────────────────────── */
int main(void) {
    signal(SIGINT, sig_handler);

    getcwd(cwd, sizeof(cwd));
    print_banner();
    cmd_uptime();
    printf("\n");

    char line[MAX_CMD];
    char *argv[MAX_ARGS];

    while (1) {
        print_prompt();

        if (!fgets(line, sizeof(line), stdin)) {
            /* EOF → continue */
            printf("\n");
            continue;
        }

        /* 개행 제거 */
        line[strcspn(line, "\n")] = '\0';
        if (!line[0]) continue;

        int argc = parse_args(line, argv);
        if (argc == 0) continue;

        const char *cmd = argv[0];

        if (strcmp(cmd, "exit") == 0 || strcmp(cmd, "quit") == 0) {
            printf(GREEN "\n  Uptime Kernel 종료 중...\n" RESET);
            printf(CYAN "  IgnisOS 데스크톱 부팅을 시작합니다.\n\n" RESET);
            break;
        } else if (strcmp(cmd, "ls") == 0) {
            cmd_ls(argv[1]);
        } else if (strcmp(cmd, "cd") == 0) {
            if (!argv[1]) {
                chdir(getenv("HOME") ?: "/");
            } else if (chdir(argv[1]) != 0) {
                printf(RED "cd: %s: %s\n" RESET, argv[1], strerror(errno));
            }
        } else if (strcmp(cmd, "pwd") == 0) {
            getcwd(cwd, sizeof(cwd));
            printf("%s\n", cwd);
        } else if (strcmp(cmd, "mkdir") == 0) {
            cmd_mkdir(argv[1]);
        } else if (strcmp(cmd, "rmdir") == 0) {
            cmd_rmdir(argv[1]);
        } else if (strcmp(cmd, "rm") == 0) {
            cmd_rm(argv[1]);
        } else if (strcmp(cmd, "touch") == 0) {
            cmd_touch(argv[1]);
        } else if (strcmp(cmd, "cat") == 0) {
            cmd_cat(argv[1]);
        } else if (strcmp(cmd, "cp") == 0) {
            cmd_cp(argv[1], argv[2]);
        } else if (strcmp(cmd, "mv") == 0) {
            cmd_mv(argv[1], argv[2]);
        } else if (strcmp(cmd, "uptime") == 0) {
            cmd_uptime();
        } else if (strcmp(cmd, "uname") == 0) {
            cmd_uname();
        } else if (strcmp(cmd, "calc") == 0) {
            cmd_calc(argc, argv);
        } else if (strcmp(cmd, "clear") == 0 || strcmp(cmd, "cls") == 0) {
            printf("\033[2J\033[H");
            print_banner();
        } else if (strcmp(cmd, "help") == 0 || strcmp(cmd, "?") == 0) {
            cmd_help();
        } else {
            printf(RED "  명령어를 찾을 수 없습니다: " RESET "'%s' "
                   DIM "(help 입력 시 목록 확인)\n" RESET, cmd);
        }
    }

    return 0;
}
