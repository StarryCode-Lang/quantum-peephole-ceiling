# Quarl Reproduction Guide

## 1. Introduction 

Welcome to the Quarl Artifact guide. This document outlines the steps necessary to replicate the findings of the Quarl research paper.
- Hardware Dependencies and Access: The second section details the required hardware dependencies and guides you on accessing the Catalyst cluster. Access credentials will be distributed through our communication channel during the "kick-the-tires" phase.

- Environment Setup: The third section focuses on setting up the necessary environment for evaluation. It includes instructions for pulling a pre-configured Docker image and also provides guidance for those who prefer to manually build the environment.

- Reproducing Experimental Results: The fourth section offers comprehensive instructions for replicating the experiments detailed in the Quarl paper. Due to the time-intensive nature of these experiments, we include one or two runs per table or figure as examples, demonstrating the reproducibility of our results.

## 2. Hardware Dependencies

### Training Requirements

- The reinforcement learning agent in Quarl necessitates the use of GPUs for training.
- For the results presented in Table 2, 3, 4 and Figure 12 of the original paper, machines equipped with A100 GPUs were employed.
- Machines with V100 GPUs were used for the ablation studies.

### Access to Hardware

- Due to the current GPU shortages, the specific hardware (A100 and V100 GPUs) used in our study is not available for artifact evaluation.

- We provide access to the CMU Catalyst Cluster as an alternative. However, it is important to note that this cluster is equipped with Nvidia A5000 GPUs, which differ in performance characteristics from the A100 and V100 GPUs used in our study.

- Cluster Specifications:
    - Each node in the cluster includes:
        - 128 CPU cores.
        - 512 GB of memory.
        - 4 A5000 GPUs with 24 GB of GPU memory each.
    - Access details:
        - Username: ?????
        - Password: ?????
    - Launching an Interactive Node:
        - For artifact evaluation, reviewers will need to launch an interactive node on the CMU Catalyst Cluster, which is managed by Slurm. Detailed instructions for launching an interactive session with Slurm are provided in the Get Started section.

### Impact on Results Reproduction

- Due to the change in hardware, especially the use of A5000 GPUs instead of A100s and V100s, it may not be possible to fully reproduce the results presented in the paper, particularly those that are sensitive to the specific GPU performance or have time constraints.

- We recommend that reviewers take this hardware discrepancy into account when evaluating the artifact.

## 3. Get Started

### Logging in and Launching a Node on the Catalyst Cluster

#### Logging in

To access the Catalyst Cluster, use SSH with the following command:

```bash
ssh aaa@catalyst-cluster.cs.cmu.edu
```

This command logs you into the login node of the Catalyst Cluster.

#### Launching an Interactive Node with Slurm

Once logged in, you can launch an interactive node for your evaluation using Slurm. Use the command:

```bash
salloc --nodes=1 --ntasks-per-node=1 --cpus-per-task=128 --mem=512G --gres=gpu:4 --time=01:00:00
```

Here, the `--time=01:00:00` parameter specifies a 1-hour allocation, which you can adjust as needed. This command requests a node with the specified resources.

After executing this command, Slurm will allocate a node and inform you which node has been allocated, as shown below:

```
salloc: Nodes catalyst-0-11 are ready for job
```

#### Accessing the Allocated Node

To access the allocated node, use SSH again:

```bash
ssh catalyst-0-11
```

Replace `catalyst-0-11` with the actual node name provided by Slurm.


### Docker (Recommended for Evaluation)

To use already setup environment, start the docker container via the following command.

```shell
docker run --name quarl --gpus all -itd co1lin/quarl
docker exec -it quarl zsh
cd quarl-artifact # /home/ubuntu/quarl-artifact
git pull && git checkout quarl-repro
```

### Manual Setup (Recommended for Development)

You can ignore this section if you use docker to set up the environment.

1. Setup the Python environment with [mamba](https://github.com/quantum-compiler/Quarl-artifact/blob/master/INSTALL.md#install-from-source). 

2. Install Quartz following [this section](https://github.com/quantum-compiler/Quarl-artifact/blob/master/INSTALL.md#install-from-source), in which a mamba (conda) environment `quartz` is created.

3. Install packages for Quarl:

    ```shell
    # at the root dir of quarl-artifact repo
    git checkout quarl-repro
    cd experiment/ppo-new
    mamba activate quartz
    mamba env update --file env_ppo.yml
    ```

    After the installation completes, check if the GPU-enabled PyTorch is installed. If not (only the CPU version is installed), uninstall `torch` via `pip` and install the GPU-enabled PyTorch following the instruction on its official website.

### Weights & Biases Setup

#### Logging into the Weights & Biases (wandb) account

To maintain the anonymity of reviewers, a dedicated wandb account has been created and will be provided in the communication channel during the kick-the-tires phase.

Once logged into the wandb account, you need to obtain an API key. This key is used for authentication when logging into wandb on the cluster node. To get your API key, follow these steps:

- Log into the wandb website with the provided account credentials.
- Navigate to your account settings or API section to find your API key.

After obtaining your API key, you can log into wandb on the cluster node using the following command:


```bash
wandb login
```

When prompted, enter the API key you obtained from the wandb account.


### Preparing

Run the following commands to enter the experiments directory and create directory for log:

```shell
# at the root dir of quarl-artifact repo
git checkout quarl-repro
cd experiment/ppo-new # this is the folder for Quarl experiments
mkdir ftlog
```

## 4. Instructions for Evaluation

In this section, we provide step-by-step instructions to evaluate the functionality of the artifact. For every experimental result in the Quarl paper, we provide instructions to reproduce it. We also provide scaled-down examples to help check the reusability of the scripts.

All the Quarl experiments are conducted by running the `ppo.py` file. The local outputs are found in directory `outputs/`, and the real-time value of the metrics can be viewed from wandb project webpages (e.g. https://wandb.ai/userXYZ/IBM-Finetune-6l-seed).

### Pre-training


### Table 2 and 3

#### Quarl's Results

Run the following commands to reproduce the results of Quarl without the rotation merging preprocessing pass.
The provided command run the experiment on 2 circuits, namely mod_red_21 and adder_8.
Modify the value of the argument `CIRC` to run on other circuits.

```shell
# w/o rotation merging pre-processing
CKPT=ckpts/nam2_iter_384_6l.pt BS=4800 CIRC=mod_red_21 GPU=0 bash scripts/nam2_search.sh
CKPT=ckpts/nam2_iter_384_6l.pt BS=3200 CIRC=adder_8 GPU=1 bash scripts/nam2_search.sh
```

Run the following command to reproduce the results of Quarl with the rotation merging preprocessing pass.
The provided command run the experiment on 2 circuits, namely mod_red_21 and adder_8.
Modify the value of the argument `CIRC` to run on other circuits.


```shell
# w/ rotation merging pre-processing
CKPT=ckpts/nam2_rm_iter_404_6l.pt BS=4800 CIRC=mod_red_21 GPU=2 bash scripts/nam2_rm_search.sh
CKPT=ckpts/nam2_rm_iter_404_6l.pt BS=3200 CIRC=adder_8 GPU=3 bash scripts/nam2_rm_search.sh
```

The result of a run is presented as a chart on the wandb website of the corresponding run whose name has the postfix `min_gate_count_iter` (e.g. `mod_red_21_min_gate_count_iter`).

Results in Table 3 are obtained from the same set of experiments as Table 2.

#### Nam

Nam's results are obtained from the [paper](https://www.nature.com/articles/s41534-018-0072-4).

#### VOQC

Enter the root of the repo, and then enter the directory `experiment/comparison/`.
Run `python VOQC_nam.py`.

#### Qiskit

Enter the root of the repo, and then enter the directory `experiment/comparison/`.
Run `python Qiskit_nam.py`.

#### t|ket $\rangle$

Enter the root of the repo, and then enter the directory `experiment/comparison/`.
Run `python tket_nam.py`.

#### Quartz

Enter the root of the repo, and then enter the directory `experiment/comparison/`.
Run `python quartz_nam_worm.py` to run Quartz without the rotation merging preprocessing pass.
Run `python quartz_nam_rm.py` to run Quartz with the rotation merging preprocessing pass.

### Table 4

#### Quarl's Results

The provided command run the experiment on 2 circuits, namely barenco_tof_10 and adder_8.
Modify the value of the argument `CIRC` to run on other circuits.

```shell
CKPT=ckpts/ibm_iter_921_6l.pt BS=4800 CIRC=barenco_tof_10 GPU=0 bash scripts/ibm_search_6l.sh
CKPT=ckpts/ibm_iter_921_6l.pt BS=2400 CIRC=adder_8 GPU=1 bash scripts/ibm_search_6l.sh
```

#### Qiskit

Enter the root of the repo, and then enter the directory `experiment/comparison/`.
Run `python Qiskit_ibm.py`.

#### t|ket $\rangle$

Enter the root of the repo, and then enter the directory `experiment/comparison/`.
Run `python tket_ibm.py`.

#### Quartz

Enter the root of the repo, and then enter the directory `experiment/comparison/`.
Run `python quartz_ibm.py`.

### Ablation Study

#### Figure 8. Local Decoding vs. Global Decoding

To run the local decoding (default in Quarl), run the following command:

```shell
git checkout quarl-repro
BS=4800 CIRC=mod_red_21 GPU=0 bash scripts/ibm_search_6l_wops.sh
```

Modify the argument `CIRC` to run on other circuits.

To run the global decoding experiments, run the following command:

```shell
git checkout rl-ablation-local-decoding
BS=4800 CIRC=mod_red_21 GPU=0 bash scripts/ibm_search_6l_loc.sh
```

Modify the argument `CIRC` to run on other circuits.

#### Figure 9. HAE vs. GAE

To run HAE (default in Quarl), run the following command:

```shell
git checkout quarl-repro
BS=4800 CIRC=mod_red_21 GPU=0 bash scripts/ibm_search_6l_wops.sh
```

Modify the argument `CIRC` to run on other circuits.

To run the GAE experiments, run the following command:

```shell
git checkout rl-ablation-advantage-estimation
BS=4800 CIRC=mod_red_21 GPU=0 bash scripts/ibm_search_6l_gae.sh
```

Modify the argument `CIRC` to run on other circuits.

#### Figure 10. The Influence of Pre-training

To run Quarl with pre-training (default in Quarl), run the following command:

```shell
git checkout quarl-repro
CKPT=ckpts/ibm_iter_921_6l.pt BS=4800 CIRC=portfoliovqe_8 GPU=0 bash scripts/ibm_search_6l.sh
```

Modify the argument `CIRC` to run on other circuits.

To run Quarl without pretraining, run the following command:

```shell
git checkout quarl-repro
BS=4800 CIRC=portfoliovqe_8 GPU=0 bash scripts/ibm_search_wops.sh
```

Modify the argument `CIRC` to run on other circuits.

#### Figure 11. The Influence of Policy-guided Search

To run Quarl with the policy-guided search (default in Quarl), run the following command:

```shell
git checkout quarl-repro
CKPT=ckpts/ibm_iter_921_6l.pt BS=4800 CIRC=portfoliovqe_8 GPU=0 bash scripts/ibm_search_6l.sh
```

Modify the argument `CIRC` to run on other circuits.

To run the GAE experiments, run the following command:

```shell
git checkout quarl-repro
CKPT=ckpts/ibm_iter_921_6l.pt BS=4800 CIRC=barenco_tof_10 GPU=0 bash scripts/ibm_search_wos.sh
```

Modify the argument `CIRC` to run on other circuits.
