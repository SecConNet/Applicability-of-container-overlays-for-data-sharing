"""
This script creates a yaml and bash file for a policy. The bash script is
to label existing pods with the policy labels.

"""

import json
import sys
import os

# This is a template which is used when no ingress and no egress is allowed
# from/to a pod.
base_policy = "\
apiVersion: cilium.io/v2\n\
kind: CiliumNetworkPolicy\n\
metadata:\n\
  name: {}\n\
spec:\n\
  endpointSelector:\n\
    matchLabels:\n\
      id.pod: {}\n\
  ingress:\n\
  - {{}}\n\
  egress:\n\
  - {{}}\n\
"

# This is a template which is used when only ingress is allowed from a pod.
ingress_only = "\
apiVersion: cilium.io/v2\n\
kind: CiliumNetworkPolicy\n\
metadata:\n\
  name: {}\n\
spec:\n\
  endpointSelector:\n\
    matchLabels:\n\
      id.pod: {}\n\
  ingress:\n\
  - fromEndpoints:\n\
    - matchLabels:\n\
        id.pod: {}\n\
  egress:\n\
  - {{}}\n\
"

# This is a template which is used when only egress is allowed to a pod.
egress_only = "\
apiVersion: cilium.io/v2\n\
kind: CiliumNetworkPolicy\n\
metadata:\n\
  name: {}\n\
spec:\n\
  endpointSelector:\n\
    matchLabels:\n\
      id.pod: {}\n\
  ingress:\n\
  - {{}}\n\
  egress:\n\
  - toEndpoints:\n\
    - matchLabels:\n\
        id.pod: {}\n\
"

# This is a template which is used when both ingress and egress is allowed
# from/to a pod.
egress_ingress = "\
apiVersion: cilium.io/v2\n\
kind: CiliumNetworkPolicy\n\
metadata:\n\
  name: {}\n\
spec:\n\
  endpointSelector:\n\
    matchLabels:\n\
      id.pod: {}\n\
  ingress:\n\
  - fromEndpoints:\n\
    - matchLabels:\n\
        id.pod: {}\n\
  egress:\n\
  - toEndpoints:\n\
    - matchLabels:\n\
        id.pod: {}\n\
"

def add_egress(dictio, vm, pod, to):
    d = dictio[vm]
    if (pod not in d) and (to is None):
        d[pod] = ([], [])
    if pod not in d:
        d[pod] = ([], [to])
    elif (to is not None):
        l = d[pod][1]
        if to not in l:
            l.append(to)

def add_ingress(dictio, vm, pod, from_):
    d = dictio[vm]
    if pod not in d:
        d[pod] = ([from_], [])
    else:
        l = d[pod][0]
        if from_ not in l:
            l.append(from_)

def write_delimiter(out, first):
    if (not first):
        out.write("---\n")

    return False

def gen_policy(scen, output, prefix):
    vms = scen["VMs"]
    policy_data = {}
    for vm in vms:
        policy_data[vm] = {}

    names = scen["VMpodnames"]
    for c, vm in enumerate(vms):
        vm_pols = scen["policies"][c]
        if len(vm_pols) == 0:
            continue

        for pol in vm_pols:
            if len(pol[1]) == 0:
                name1 = names[c][pol[0]]
                add_egress(policy_data, c, name1, None)
            else:
                ingress_vm = pol[1][0]
                ingress_pods = pol[1][1]
                for pod in ingress_pods:
                    name1 = names[c][pol[0]]
                    name2 = names[ingress_vm][pod]
                    add_egress(policy_data, vm, name1, (vms[ingress_vm], name2))
                    add_ingress(policy_data, vms[ingress_vm], name2, (vm, name1))

    # Forbid communication if no ingress/egress rules defined
    first = True
    with open(output, 'a') as out:
        for vm, data in policy_data.items():
            for pod, (ingress, egress) in data.items():
                if (not ingress) and (not egress):
                    first = write_delimiter(out, first)
                    out.write(base_policy.format(f"{prefix}-{pod}-isolated", f"{prefix}-{pod}"))
                else:
                    for ingress_rule in ingress:
                        other_vm = ingress_rule[0]
                        other_pod = ingress_rule[1]
                        first = write_delimiter(out, first)
                        if ingress_rule in egress:
                            out.write(egress_ingress.format(f"{prefix}-{pod}-egress-ingress-{other_pod}", f"{prefix}-{pod}", f"{prefix}-{other_pod}", "id.pod", f"{prefix}-{other_vm}-{other_pod}"))
                            egress.remove(ingress_rule)
                        else:
                            out.write(ingress_only.format(f"{prefix}-{pod}-ingress-{other_pod}", f"{prefix}-{pod}", f"{prefix}-{other_pod}"))

                    for other_vm, other_pod in egress:
                        first = write_delimiter(out, first)
                        out.write(egress_only.format(f"{prefix}-{pod}-egress-{other_pod}", f"{prefix}-{pod}", f"{prefix}-{other_pod}"))

    return policy_data


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 gen_policies.py <gen id> <pods.json> <scenario.json> <output.yaml>")
    else:
        prefix = sys.argv[1]
        podfile = sys.argv[2]
        file = sys.argv[3]
        output = sys.argv[4]
        try:
            os.remove(output)
        except OSError:
            pass

        with open(podfile) as pf:
            with open(file) as f:
                scen = json.load(f)
                tmp = json.load(pf)
                for key, val in tmp.items():
                    scen[key] = val

                policy_data = gen_policy(scen, output, prefix)
                # gen_pod_labels(scen, outputsh, policy_data, prefix)
                # gen_pods(scen, output, policy_data)
