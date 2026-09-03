OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
u3(3*pi/4,-pi/2,pi/2) q[0];
u3(3*pi/4,pi/2,-pi/2) q[1];
u2(-pi/2,pi/2) q[2];
u3(pi/4,-pi/2,pi/2) q[3];