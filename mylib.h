#ifndef MYLIB_H
#define MYLIB_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef long long df_value_t;


int load_trace(const char *path);

const df_value_t* get_data(size_t* n);

#ifdef __cplusplus
}
#endif

#endif
