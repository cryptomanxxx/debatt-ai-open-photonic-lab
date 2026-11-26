/* Independent FP64 Moller-Trumbore triangle classifier, no epsilon.
 * -1: coplanar nondegenerate (outside contract), 0: miss, 1: hit.
 * Degenerate triangles have no surface hit. Distance is ray parameter t.
 */
#include <stddef.h>
static void sub(const double *a,const double *b,double *c) {
    for(int k=0;k<3;k++) c[k]=a[k]-b[k];
}
static void cross(const double *a,const double *b,double *c) {
    c[0]=a[1]*b[2]-a[2]*b[1];
    c[1]=a[2]*b[0]-a[0]*b[2];
    c[2]=a[0]*b[1]-a[1]*b[0];
}
static double dot(const double *a,const double *b) {
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
}
int triangle(const double *o,const double *d,const double *v,double *t) {
    double e[3],f[3],n[3],p[3],s[3],q[3];
    sub(v+3,v,e);sub(v+6,v,f);cross(e,f,n);
    if(n[0]==0 && n[1]==0 && n[2]==0) return 0;
    sub(o,v,s);cross(d,f,p);
    double det=dot(e,p);
    if(det==0) return dot(n,s)==0 ? -1 : 0;
    double u=dot(s,p)/det;
    cross(s,e,q);
    double w=dot(d,q)/det;
    double z=dot(f,q)/det;
    if(u<0 || w<0 || u+w>1 || z<0) return 0;
    *t=z;return 1;
}
