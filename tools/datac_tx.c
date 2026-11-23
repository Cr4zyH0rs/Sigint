/* Minimal codec2 data-mode (DATAC*) burst transmitter using libcodec2 freedv_api (codec2 1.2.0).
   Usage: datac_tx MODE NFRAMES SEED > out.raw  (signed 16-bit, 8 kHz)
   MODE: DATAC0, DATAC1, DATAC3, DATAC4, DATAC13. One burst = preamble, NFRAMES modem frames of
   random payload (with the CRC16 the API expects), postamble. Payload is random (ID-only). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <codec2/freedv_api.h>
int main(int argc, char **argv) {
    if (argc < 4) return 1;
    int mode = !strcmp(argv[1], "DATAC0") ? FREEDV_MODE_DATAC0 : !strcmp(argv[1], "DATAC1") ? FREEDV_MODE_DATAC1 :
               !strcmp(argv[1], "DATAC3") ? FREEDV_MODE_DATAC3 : !strcmp(argv[1], "DATAC4") ? FREEDV_MODE_DATAC4 :
               !strcmp(argv[1], "DATAC13") ? FREEDV_MODE_DATAC13 : -1;
    if (mode < 0) { fprintf(stderr, "bad mode\n"); return 1; }
    int nframes = atoi(argv[2]); srand(atoi(argv[3]));
    struct freedv *f = freedv_open(mode);
    int nbytes = freedv_get_bits_per_modem_frame(f) / 8;
    int nmax = freedv_get_n_tx_modem_samples(f);
    int npre = freedv_get_n_tx_preamble_modem_samples(f), npost = freedv_get_n_tx_postamble_modem_samples(f);
    if (npre > nmax) nmax = npre; if (npost > nmax) nmax = npost;
    short *mo = malloc(sizeof(short) * nmax);
    unsigned char *b = malloc(nbytes);
    int n = freedv_rawdatapreambletx(f, mo); fwrite(mo, sizeof(short), n, stdout);
    for (int k = 0; k < nframes; k++) {
        for (int i = 0; i < nbytes - 2; i++) b[i] = rand() & 0xff;
        unsigned short crc = freedv_gen_crc16(b, nbytes - 2);
        b[nbytes - 2] = crc >> 8; b[nbytes - 1] = crc & 0xff;
        freedv_rawdatatx(f, mo, b);
        fwrite(mo, sizeof(short), freedv_get_n_tx_modem_samples(f), stdout);
    }
    n = freedv_rawdatapostambletx(f, mo); fwrite(mo, sizeof(short), n, stdout);
    freedv_close(f); return 0;
}
