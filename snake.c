#include <assert.h>
#include <signal.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
#ifndef _WIN32
#include <bits/pthreadtypes.h>
#endif


#ifdef _WIN32
#include <conio.h>
#define __useconds_t useconds_t
#else
#include <termio.h>
extern void cfmakeraw (struct termios *__termios_p) __THROW;
static pthread_mutex_t GETCH_OLD_LOCK = PTHREAD_MUTEX_INITIALIZER;
static atomic_bool GETCH_TERM_SETTED = false;
static struct termios GETCH_OLD;

int getch_setterm_to_normal() {
    if (GETCH_TERM_SETTED) {
        pthread_mutex_lock(&GETCH_OLD_LOCK);
        if (tcsetattr(
                0,
                TCSANOW,
                &GETCH_OLD
            ) < 0)
        {
            pthread_mutex_unlock(&GETCH_OLD_LOCK);
            return -1;
        }
        GETCH_TERM_SETTED = false;
        pthread_mutex_unlock(&GETCH_OLD_LOCK);
    }
    return 0;
}
/* get char, but no line buffer */
int getch(void) {
    // from https://zhuanlan.zhihu.com/p/32494610
    struct termios tm;
    int fd = 0, ch;

    if (tcgetattr(fd, &tm) < 0) {
        return -1;
    }

    pthread_mutex_lock(&GETCH_OLD_LOCK);
    GETCH_OLD = tm;
    GETCH_TERM_SETTED = true;
    pthread_mutex_unlock(&GETCH_OLD_LOCK);

    cfmakeraw(&tm);
    if (tcsetattr(fd, TCSANOW, &tm) < 0) {
        return -1;
    }

    ch = getchar();
    getch_setterm_to_normal();

    return ch;
}
#endif

extern int usleep (__useconds_t __useconds);


#define CSI_END ((int)-1)
#define loop for (;;)

typedef unsigned char byte_t;
typedef atomic_uchar atomic_byte_t;

static atomic_bool BAK_SCREEN_OPEN = false;
#define MAP_WIDTH ((int)40)
#define MAP_HEIGHT ((int)30)
const int INIT_SNAKE_BODY_LEN = 3;
const int INIT_SNAKE_X = 0;
const int INIT_SNAKE_Y = 0;

int trand() {
    return rand();
}

struct Pos {
    int x, y;
};
struct Pos pos_make(int x, int y) {
    struct Pos res = { x, y };
    return res;
}
struct BodyData {
    byte_t rotate   : 2;
    bool is_body    : 1,
         is_food    : 1;
};
struct BodyData body_data_make(byte_t rotate, bool is_body, bool is_food) {
    struct BodyData data = {
        .rotate  = rotate,
        .is_body = is_body,
        .is_food = is_food,
    };
    return data;
}
enum Color {
    HEAD_COLOR = 101,
    BODY_COLOR = 107,
    FOOD_COLOR = 102,
    FOODED_BODY_COLOR = 106,
    BOX_COLOR = 43,
    NONE_COLOR = 49,
};

typedef struct BodyData Map[MAP_WIDTH][MAP_HEIGHT];

void csi(int head, ...) {
    if (head == CSI_END) {
        printf("\x1b[");
        return;
    }
    va_list ap;
    va_start(ap, head);
    int num;
    printf("\x1b[%d", head);
    while ((num = va_arg(ap, int)) != CSI_END) {
        printf(";%d", num);
    }
    va_end(ap);
}
void cursor_to_pos(int x, int y) {
    csi(y+1, x*2+1, CSI_END);
    printf("H");
    fflush(stdout);
}
void hl_open(enum Color color) {
    csi((int)color, CSI_END);
    printf("m");
}
void hl_close() {
    csi(NONE_COLOR, CSI_END);
    printf("m");
}
void hl_pos(struct Pos pos, enum Color color) {
    int x = pos.x, y = pos.y;

    csi(CSI_END);
    printf("s");

    hl_open(color);
    cursor_to_pos(x, y);
    printf("  ");
    hl_close();

    csi(CSI_END);
    printf("u");

    fflush(stdout);
}
void bak_screen(bool stat) {
    csi(CSI_END);
    printf("?1049");
    if (stat) printf("h");
    else printf("l");
    fflush(stdout);
    BAK_SCREEN_OPEN = stat;
}
void clear(bool inline_) {
    hl_close();
    csi(CSI_END);
    if (inline_)
        printf("2K");
    else
        printf("2J");
    fflush(stdout);
}
void clear_to_end(bool inline_) {
    hl_close();
    csi(CSI_END);
    if (inline_)
        printf("K");
    else
        printf("J");
    fflush(stdout);
}
void cursor_move(int x, int y) {
    if (x < 0) { csi(x, CSI_END); printf("A"); }
    if (x > 0) { csi(x, CSI_END); printf("B"); }
    if (y < 0) { csi(y, CSI_END); printf("D"); }
    if (y > 0) { csi(y, CSI_END); printf("C"); }
    fflush(stdout);
}
void sig_handler(int sig) {
    switch (sig) {
    case SIGINT:
    case SIGTERM:
#ifndef _WIN32
        getch_setterm_to_normal();
#endif
        if (BAK_SCREEN_OPEN) {
            bak_screen(false);
        }
        printf("use sigint exit!\n");
        exit(0);
    }
}
void map_pos_rewind(int *x, int *y) {
    while (*x < 0) *x += MAP_WIDTH;
    *x %= MAP_WIDTH;

    while (*y < 0) *y += MAP_HEIGHT;
    *y %= MAP_HEIGHT;
}
void display_box() {
    int i;
    for (i = 0; i < MAP_WIDTH; i++) {
        hl_pos(pos_make(i, MAP_HEIGHT), BOX_COLOR);
    }
    for (i = 0; i <= MAP_HEIGHT; i++) {
        hl_pos(pos_make(MAP_WIDTH, i), BOX_COLOR);
    }
}
void print_help() {
    printf(
            "wasd / hjkl: change move direction\n"
            "r: redraw box\n"
            "R: clear screen\n"
            "+/-: change sleep time\n"
            "space: pause\n"
            "Q: exit\n"
    );
}

struct Snake {
    Map map;
    byte_t head_rotate;
    struct Pos head, tail, food;
    unsigned int score;
};
struct Pos get_pos_inc(byte_t rotate) {
    switch (rotate) {
    case 0: return pos_make(1,  0);
    case 1: return pos_make(0,  1);
    case 2: return pos_make(-1, 0);
    case 3: return pos_make(0,  -1);
    }
    return pos_make(0, 0);
}
void pos_inc(byte_t rotate, int *x, int *y) {
    struct Pos pos = get_pos_inc(rotate);
    *x += pos.x;
    *y += pos.y;
    map_pos_rewind(x, y);
}
enum Color snake_get_color(struct Snake *self, struct Pos pos) {
    struct BodyData *data = &self->map[pos.x][pos.y];
    switch (data->is_body << 1 | data->is_food) {
    case 0b00: return NONE_COLOR;
    case 0b01: return FOOD_COLOR;
    case 0b10: return BODY_COLOR;
    case 0b11: return FOODED_BODY_COLOR;
    }
    assert(false);
}
void snake_hl_pos(struct Snake *self, struct Pos pos) {
    enum Color color = snake_get_color(self, pos);
    hl_pos(pos, color);
}
void snake_update_food(struct Snake *self) {
    int *x, *y;
    x = &self->food.x;
    y = &self->food.y;

    bool prev_food = self->map[*x][*y].is_food;
    self->map[*x][*y].is_food = false;
    snake_hl_pos(self, self->food);
    self->map[*x][*y].is_food = prev_food;

    do {
        *x = trand();
        *y = trand();
        map_pos_rewind(x, y);
    } while (self->map[*x][*y].is_body);
    self->map[*x][*y].is_food = true;
}
struct Snake *snake_make() {
    struct Snake *self = malloc(sizeof(struct Snake));

    for (int x = 0; x < MAP_WIDTH; x++) { // empty init
        for (int y = 0; y < MAP_HEIGHT; y++) {
            struct BodyData data = { 0, 0, 0 };
            self->map[x][y] = data;
        }
    }
    const int head = INIT_SNAKE_X + INIT_SNAKE_BODY_LEN;
    for (int x = INIT_SNAKE_X; x < head; x++) { // snake init
        struct BodyData data = {
            .rotate  = 0,
            .is_body = 1,
            .is_food = 0,
        };
        self->map[x][INIT_SNAKE_Y] = data;
    }
    // head init
    self->head = pos_make(head, INIT_SNAKE_Y);
    self->head_rotate = 0;
    // tail init
    self->tail = pos_make(INIT_SNAKE_X, INIT_SNAKE_Y);

    self->score = 0;

    snake_update_food(self);

    return self;
}
void snake_init_display(struct Snake *self) {
    snake_hl_pos(self, self->food);
    int x, y;
    x = self->tail.x;
    y = self->tail.y;
    while (x != self->head.x || y != self->head.y) {
        snake_hl_pos(self, pos_make(x, y));
        pos_inc(self->map[x][y].rotate, &x, &y);
    }
    hl_pos(self->head, HEAD_COLOR);
}
bool snake_do_move(struct Snake *self) {
    byte_t rotate = self->head_rotate;
    struct BodyData *data;
    bool is_dead = false;

    int *x = &self->head.x, *y = &self->head.y;
    data = &self->map[*x][*y];
    data->is_body = true;
    data->rotate = rotate;
    pos_inc(rotate, x, y);
    if (data->is_food) {
        snake_update_food(self);
    }
    is_dead |= self->map[*x][*y].is_body;

    // move tail
    data = &self->map[self->tail.x][self->tail.y];
    if (!data->is_food) {
        struct Pos *tail = &self->tail, preset_tail = *tail;
        pos_inc(data->rotate, &tail->x, &tail->y);
        *data = body_data_make(0, 0, 0);
        snake_hl_pos(self, preset_tail);
    } else {
        { // 每吃一定的食物刷新box, 省的小概率出问题时需要手动刷新
            static atomic_byte_t update_box_count = 0;
            update_box_count += 1;
            if (!(update_box_count %= 3)) {
                display_box();
            }
        }
    }
    self->score += data->is_food;
    data->is_food = false;

    snake_init_display(self);

    return is_dead;
}
void snake_set_rotate(struct Snake *self, byte_t rotate) {
    if ((rotate+2 & 0b11) == self->head_rotate) return;
    self->head_rotate = rotate;
}

struct UserInputData {
    atomic_bool finished;
    atomic_byte_t next_rotate;
    atomic_int sleep_time;
    atomic_bool pause;
};
void *user_input_handle(void *raw_data) {
    struct UserInputData *data = raw_data;

    while (!data->finished) {
        switch (getch()) {
        case ' ':
            data->pause = !data->pause;
            break;
        case '+':
            data->sleep_time += 10;
            printf("\n" "sleep_time: %d", data->sleep_time);
            break;
        case '-':
            data->sleep_time = data->sleep_time <= 30
                ? 20
                : data->sleep_time - 10;
            printf("\n" "sleep_time: %d", data->sleep_time);
            break;
        case '?':
            printf("\n");
            print_help();
            break;
        case 'R':
            clear(false);
        case 'r':
            display_box();
            break;
        case 'Q':
            data->finished = true;
            break;
        case '\003':
            sig_handler(SIGINT);
            return NULL;
        case 'l': case 'd': data->next_rotate = 0; break;
        case 'j': case 's': data->next_rotate = 1; break;
        case 'h': case 'a': data->next_rotate = 2; break;
        case 'k': case 'w': data->next_rotate = 3; break;
        }
        clear_to_end(true);
        cursor_move(0, 1);
        clear_to_end(false);
        cursor_move(0, -1);
    }

    return NULL;
}

int main(int argc, char *argv[]) {
    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    bak_screen(true);

    struct Snake *snake = snake_make();

    pthread_t tid;
    struct UserInputData *input_data = malloc(sizeof(struct UserInputData));
    input_data->finished = false;
    input_data->next_rotate = -1;
    input_data->sleep_time = 100;
    input_data->pause = false;
    pthread_create(&tid, NULL, &user_input_handle, input_data);

    display_box();

    bool is_dead = false;
    loop {
        if (input_data->finished) break;
        int next_rotate;
        if ((next_rotate = input_data->next_rotate) != (byte_t)-1) {
            snake_set_rotate(snake, next_rotate);
        }
        is_dead = snake_do_move(snake);
        cursor_to_pos(0, MAP_HEIGHT+1);
        if (is_dead) {
            printf("You're dead, press any key to settle score.\n");
            break;
        }
        printf("input `?` print help, score: %d", snake->score);
        do
            usleep(input_data->sleep_time * 1000);
        while (input_data->pause);
    }

    input_data->finished = true;

    pthread_join(tid, NULL);

    bak_screen(false);
    if (is_dead) {
        printf("You're dead! ");
    }
    printf("score: %d\n", snake->score);
    return 0;
}
