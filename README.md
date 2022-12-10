# Applicability of container overlays for data sharing
This repository includes the codes for evaluating the capbability of two container overlay technologies (Cilium and Calico) for data sharing application.


It includes below files:
1. [/Applicability-of-container-overlays-for-data-sharing/gen_pods] </gen_pods.py> : For a given json file which defines pods that should be launched on some nodes, this script creates yaml files which can spawn these pods.

2. [/Applicability-of-container-overlays-for-data-sharing/gen_policies] (/gen_policies.py) :It creates a yaml and bash file for a policy. The bash script is to label existing pods with the policy labels

3. [/Applicability-of-container-overlays-for-data-sharing/iperf_exp] (/Applicability-of-container-overlays-for-data-sharing/iperf_exp.sh) : This file automatically run iperf3 between two pods and stores the log of iperf3. 


