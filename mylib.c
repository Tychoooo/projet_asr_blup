#include "mylib.h"

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>
#include <string.h>

#include <fxt.h>
#include <fxt-tools.h>

#define MAX_PARAMS       16
#define FIELDS_PER_EVENT (7 + MAX_PARAMS)  // 4 champs de base + cpu + tid + raw + params

static df_value_t *DATA = NULL;
static size_t DATA_CAP   = 0;  // nombre d'événements max
static size_t DATA_SIZE  = 0;  // taille utilisée


int load_trace(const char *path)
{
    fxt_t fxt = fxt_open(path);
    if (!fxt) {
        fprintf(stderr, "Cannot open \"%s\" trace file (%s)\n",
                path, strerror(errno));
        return -1;
    }

    fxt_blockev_t evs = fxt_blockev_enter(fxt);
    struct fxt_ev_native ev;
    int ret;

    free(DATA);
    DATA      = NULL;
    DATA_CAP  = 0;
    DATA_SIZE = 0;

    size_t nb_events = 0;

    while ((ret = fxt_next_ev(evs, FXT_EV_TYPE_NATIVE,
                              (struct fxt_ev*)&ev)) == FXT_EV_OK) {

        unsigned nb = ev.nb_params;
        if (nb > MAX_PARAMS)
            nb = MAX_PARAMS;

        // Agrandir si besoin (en nombre d'évènements)
        if (nb_events == DATA_CAP) {
            size_t new_cap = (DATA_CAP == 0) ? 1024 : DATA_CAP * 2;
            df_value_t *tmp = realloc(DATA,
                                      new_cap * FIELDS_PER_EVENT
                                      * sizeof(df_value_t));
            if (!tmp) {
                perror("realloc");
                free(DATA);
                DATA = NULL;
                DATA_CAP = 0;
                //fxt_close(fxt);
                return -1;
            }
            DATA = tmp;
            DATA_CAP = new_cap;
        }

        //Printe l'évènement
        printf("Event_num = " "%zu, time = %llu, code = %lu, nb_params = %u, cpu = %ld, tid = %lu\n",
               nb_events + 1,
               (unsigned long long)ev.time,
               ev.code,
               ev.nb_params,
               ev.param[1],
               ev.user.tid);

        df_value_t *row = &DATA[nb_events * FIELDS_PER_EVENT];

        // 0 : numéro d'évènement
        row[0] = (df_value_t)(nb_events + 1);

        // 1 : time en ns
        row[1] = (df_value_t)ev.time;

        // 2 : code
        row[2] = (df_value_t)ev.code;

        // 3 : nombre de paramètres
        row[3] = (df_value_t)nb;

        // 4 : cpu
        row[4] = (df_value_t)ev.param[1];

        // 5 : tid
        row[5] = (df_value_t)ev.user.tid;

        // 6 : raw
        row[6] = (df_value_t)(uintptr_t)ev.raw;

        // 7.. : paramètres
        for (unsigned i = 0; i < MAX_PARAMS; i++) {
            if (i < nb)
                row[7 + i] = (df_value_t)ev.param[i];
            else
                row[7 + i] = 0;
        }

        nb_events++;
    }

    if (ret != FXT_EV_EOT) {
        fprintf(stderr, "Warning: FXT stopped on code %d (not end-of-trace)\n",
                ret);
    }

    //fxt_close(fxt);

    // Taille totale du buffer en éléments
    DATA_SIZE = nb_events * FIELDS_PER_EVENT;
    return 0;
}


const df_value_t* get_data(size_t* n)
{
    if (!n)
        return NULL;
    *n = DATA_SIZE;
    return DATA;
}
