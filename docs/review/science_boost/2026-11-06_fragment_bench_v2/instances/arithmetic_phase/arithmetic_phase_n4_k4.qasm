OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
cx q[1],q[2];
rz(0.5) q[2];
cx q[1],q[2];