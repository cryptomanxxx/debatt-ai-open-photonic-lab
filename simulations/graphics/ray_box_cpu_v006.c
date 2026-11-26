/* G-004A independent scalar double-precision slab kernel.
 * Input: contiguous N x 4 x 3 doubles (origin, direction, lower, upper).
 * Output: N bytes, each 0 or 1. Closed box, forward ray.
 */
#include <stddef.h>
#include <stdint.h>
#include <math.h>

void raybox(const double *a, uint8_t *out, size_t n) {
    for (size_t i=0; i<n; ++i) {
        const double *p = a+12*i;
        double near=0.0, far=INFINITY;
        int hit=1;
        for (size_t k=0;k<3;++k) {
            double o=p[k], d=p[3+k], lo=p[6+k], hi=p[9+k];
            if (d==0.0) {
                if (o<lo || o>hi) {hit=0;break;}
                continue;
            }
            double t0=(lo-o)/d, t1=(hi-o)/d;
            if(t0>t1) {double swap=t0;t0=t1;t1=swap;}
            if(t0>near) near=t0;
            if(t1<far) far=t1;
            if(near>far) {hit=0;break;}
        }
        out[i]=(uint8_t)hit;
    }
}
