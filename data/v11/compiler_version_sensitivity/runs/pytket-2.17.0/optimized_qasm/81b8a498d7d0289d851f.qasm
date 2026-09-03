OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
u(11*pi/4,-pi/2,pi/2) q[0];
u(13*pi/4,-pi/2,pi/2) q[1];
u(pi/2,-pi/2,pi/2) q[2];
u(9*pi/4,-pi/2,pi/2) q[3];