/* Minimal FreeDV transmitter using libcodec2's freedv_api (codec2 1.2.0).
   Usage: freedv_tx_min MODE NSEC SEED > out.raw   (signed 16-bit, 8 kHz modem audio)
   MODE: 1600, 700C, 700D, 700E. Speech input is random low-level noise: the
   payload is meaningless (ID-only project). Based on the API in freedv_api.h. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <codec2/freedv_api.h>
int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: %s MODE NSEC SEED\n", argv[0]); return 1; }
    int mode = !strcmp(argv[1], "1600") ? FREEDV_MODE_1600 : !strcmp(argv[1], "700C") ? FREEDV_MODE_700C :
               !strcmp(argv[1], "700D") ? FREEDV_MODE_700D : !strcmp(argv[1], "700E") ? FREEDV_MODE_700E : -1;
    if (mode < 0) { fprintf(stderr, "bad mode\n"); return 1; }
    double nsec = atof(argv[2]); srand(atoi(argv[3]));
    struct freedv *f = freedv_open(mode);
    int ns = freedv_get_n_speech_samples(f), nm = freedv_get_n_nom_modem_samples(f);
    short *sp = malloc(sizeof(short) * ns), *mo = malloc(sizeof(short) * nm);
    long total = 0, want = (long)(nsec * freedv_get_modem_sample_rate(f));
    while (total < want) {
        for (int i = 0; i < ns; i++) sp[i] = (short)((rand() % 4001) - 2000);
        freedv_tx(f, mo, sp);
        fwrite(mo, sizeof(short), nm, stdout); total += nm;
    }
    freedv_close(f); return 0;
}
