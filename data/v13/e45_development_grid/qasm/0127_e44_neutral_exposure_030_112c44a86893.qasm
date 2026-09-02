OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
h q[0];
h q[0];
x q[1];
x q[1];
rz(0.5029999999999999) q[2];