OPENQASM 2.0;
include "qelib1.inc";
gate mcx q0,q1,q2,q3,q4 { h q4; cp(pi/2) q3,q4; h q4; h q3; t q3; cx q2,q3; tdg q3; h q3; cx q0,q3; t q3; cx q1,q3; tdg q3; cx q0,q3; t q3; cx q1,q3; tdg q3; h q3; t q3; cx q2,q3; tdg q3; h q3; h q4; cp(-pi/2) q3,q4; h q4; h q3; t q3; cx q2,q3; tdg q3; h q3; t q3; cx q1,q3; tdg q3; cx q0,q3; t q3; cx q1,q3; tdg q3; cx q0,q3; h q3; t q3; cx q2,q3; tdg q3; h q3; h q4; cp(pi/8) q0,q4; h q4; cx q0,q1; h q4; cp(-pi/8) q1,q4; h q4; cx q0,q1; h q4; cp(pi/8) q1,q4; h q4; cx q1,q2; h q4; cp(-pi/8) q2,q4; h q4; cx q0,q2; h q4; cp(pi/8) q2,q4; h q4; cx q1,q2; h q4; cp(-pi/8) q2,q4; h q4; cx q0,q2; h q4; cp(pi/8) q2,q4; h q4; }
gate mcx_2799709056144 q0,q1,q2,q3 { h q3; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q3; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; h q3; }
gate mcx_2799709045200 q0,q1,q2,q3 { h q3; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q3; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; h q3; }
gate mcx_2799709056048 q0,q1,q2,q3 { h q3; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q3; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; h q3; }
gate mcx_2799709045152 q0,q1,q2,q3 { h q3; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q3; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; h q3; }
gate mcx_2799709046352 q0,q1,q2,q3 { h q3; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q3; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; h q3; }
gate mcx_2799709045104 q0,q1,q2,q3 { h q3; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q3; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q1,q3; p(pi/8) q3; cx q2,q3; p(-pi/8) q3; cx q0,q3; h q3; }
qreg node[4];
qreg coin[1];
creg meas[5];
h coin[0];
mcx coin[0],node[1],node[2],node[3],node[0];
mcx_2799709056144 coin[0],node[2],node[3],node[1];
ccx coin[0],node[3],node[2];
cx coin[0],node[3];
x coin[0];
x node[1];
x node[2];
x node[3];
mcx coin[0],node[1],node[2],node[3],node[0];
mcx_2799709045200 coin[0],node[2],node[3],node[1];
ccx coin[0],node[3],node[2];
cx coin[0],node[3];
x node[1];
x node[2];
x node[3];
x coin[0];
h coin[0];
mcx coin[0],node[1],node[2],node[3],node[0];
mcx_2799709056048 coin[0],node[2],node[3],node[1];
ccx coin[0],node[3],node[2];
cx coin[0],node[3];
x coin[0];
x node[1];
x node[2];
x node[3];
mcx coin[0],node[1],node[2],node[3],node[0];
mcx_2799709045152 coin[0],node[2],node[3],node[1];
ccx coin[0],node[3],node[2];
cx coin[0],node[3];
x node[1];
x node[2];
x node[3];
x coin[0];
h coin[0];
mcx coin[0],node[1],node[2],node[3],node[0];
mcx_2799709046352 coin[0],node[2],node[3],node[1];
ccx coin[0],node[3],node[2];
cx coin[0],node[3];
x coin[0];
x node[1];
x node[2];
x node[3];
mcx coin[0],node[1],node[2],node[3],node[0];
mcx_2799709045104 coin[0],node[2],node[3],node[1];
ccx coin[0],node[3],node[2];
cx coin[0],node[3];
x node[1];
x node[2];
x node[3];
x coin[0];
barrier node[0],node[1],node[2],node[3],coin[0];
measure node[0] -> meas[0];
measure node[1] -> meas[1];
measure node[2] -> meas[2];
measure node[3] -> meas[3];
measure coin[0] -> meas[4];
