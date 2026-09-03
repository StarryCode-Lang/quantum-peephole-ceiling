OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
u(pi/2,0,pi) q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];