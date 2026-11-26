/* Whole BVH traversal, fixed left-first DFS, no nearest-distance pruning.
 * All storage supplied by caller. Separate compiled trace and timed variants
 * from the same template; timed variant has no trace writes or counters.
 */
#include <stddef.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

extern void raybox(const double *, uint8_t *, size_t);
extern int triangle(const double *, const double *, const double *, double *);

typedef struct {
    double lo[3], hi[3];
    int32_t left, right, first, count;
} Node;
typedef struct { int32_t id; double t; } Hit;
typedef struct {
    int32_t nv, na, nl, nt;
} Counts;

#define DEFINE_WALK(NAME, TRACE) \
static int NAME(const Node *nodes, int32_t nn, const int32_t *ids, \
    const double *tris, const double *ray, int32_t *stack, Hit *out, \
    Counts *counts, int32_t *vis, int32_t *acc, int32_t *tested) { \
    int32_t top=0, best=-1; double best_t=INFINITY; \
    if (TRACE) *counts=(Counts){0,0,0,0}; \
    stack[top++]=0; \
    while(top) { \
        int32_t j=stack[--top]; const Node *n=&nodes[j]; \
        if (TRACE) vis[counts->nv++]=j; \
        double a[12]; uint8_t yes; \
        for(int k=0;k<3;k++) {a[k]=ray[k]; a[3+k]=ray[3+k]; \
            a[6+k]=n->lo[k]; a[9+k]=n->hi[k];} \
        raybox(a,&yes,1); \
        if(!yes) continue; \
        if (TRACE) acc[counts->na++]=j; \
        if(n->left>=0) { \
            if(top>nn-2) return -1; \
            stack[top++]=n->right; stack[top++]=n->left; \
        } else { \
            if (TRACE) counts->nl++; \
            for(int32_t i=0;i<n->count;i++) { \
                int32_t p=ids[n->first+i]; double t; \
                if (TRACE) tested[counts->nt++]=p; \
                int s=triangle(ray,ray+3,tris+9*(size_t)p,&t); \
                if(s<0) return -2; \
                if(s==1 && (t<best_t || (t==best_t && (best<0 || p<best)))) { \
                    best=p; best_t=t; \
                } \
            } \
        } \
    } \
    out->id=best; out->t=best_t; return 0; \
}

DEFINE_WALK(walk_trace,1)
DEFINE_WALK(walk_fast,0)

int trace_ray(const Node *nodes,int32_t nn,const int32_t *ids,
    const double *tris,const double *ray,int32_t *stack,Hit *out,
    Counts *counts,int32_t *vis,int32_t *acc,int32_t *tested) {
    return walk_trace(nodes,nn,ids,tris,ray,stack,out,counts,vis,acc,tested);
}

int fast_batch(const Node *nodes,int32_t nn,const int32_t *ids,
    const double *tris,const double *rays,int32_t nr,int32_t *stack,Hit *out) {
    for(int32_t i=0;i<nr;i++) {
        int status=walk_fast(nodes,nn,ids,tris,rays+6*(size_t)i,stack,out+i,
                             NULL,NULL,NULL,NULL);
        if(status) return status;
    }
    return 0;
}

/* Monotonic wall clock inside native code; no Python dispatch in timed region.
 * Output writes remain part of traversal. Volatile function pointer prevents
 * eliminating repeated calls that write identical results.
 */
int time_batches(const Node *nodes,int32_t nn,const int32_t *ids,
    const double *tris,const double *rays,int32_t nr,int32_t *stack,Hit *out,
    int32_t repetitions,double *elapsed_ns) {
    struct timespec start,end;
    int (*volatile run)(const Node *,int32_t,const int32_t *,const double *,
        const double *,int32_t,int32_t *,Hit *)=fast_batch;
    if(repetitions<1 || clock_gettime(CLOCK_MONOTONIC,&start)) return -3;
    for(int32_t k=0;k<repetitions;k++) {
        int status=run(nodes,nn,ids,tris,rays,nr,stack,out);
        if(status) return status;
    }
    if(clock_gettime(CLOCK_MONOTONIC,&end)) return -3;
    *elapsed_ns=(double)(end.tv_sec-start.tv_sec)*1e9+
                (double)(end.tv_nsec-start.tv_nsec);
    return 0;
}

size_t node_size(void) {return sizeof(Node);}
size_t hit_size(void) {return sizeof(Hit);}
