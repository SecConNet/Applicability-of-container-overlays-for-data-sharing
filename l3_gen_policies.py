"""
Author: Niek van Noort

Usage: python3 l3_gen_policies.py <gen id> <pods.json> <output.yaml> <start> <end>

This script creates/replaces output.yaml. It will ouput layer 3 (l3) policies
that affect the pods defined in pod.json. The l3 rules assign ports to each
possible combination of 2 pods. The names of the policies are extended with
numbers, beginning with 'start' till 'end'.
When the range from start till end is bigger than the number of pod
combinations or when start doesn't equal 0, then l3 rules are made between
existing pods and non-exsisting pods.
"""

import json
import sys
import os

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
  egress:\n\
  - toEndpoints:\n\
    - matchLabels:\n\
        id.pod: {}\n\
"


def write_delimiter(out, first):
    """
    Write yaml delimiter if 'first' is True, always return False.
    (This function makes it possible to only skip this write the first time)
    """
    if (not first):
        out.write("---\n")

    return False


def gen_policy(scen, output, prefix, start, end):
    """
    Loop over all combinations of pods and write l4 policies for the
    combinations to 'output'.
    When the range from start till end is bigger than the number of pod
    combinations or when start doesn't equal 0, then l3 rules are made between
    existing pods and non-exsisting pods.

    (Yes this function is very ugly, I know, but I was lazy)
    """
    first = True
    vms = scen["VMs"]
    count = start
    names = scen["VMpodnames"]
    with open(output, 'a') as out:
        if start == 0:
            # For each VM
            for c1, vm in enumerate(vms):
                # For each Pod in the VM
                for p1, pod in enumerate(names[c1]):
                    # Loop through all VMs
                    for c2, other_vm in enumerate(vms):
                        # For each possible pod combination
                        for p2, other_pod in enumerate(names[c2]):
                            if c1 != c2 or p1 != p2:
                                first = write_delimiter(out, first)
                                out.write(egress_only.format(f"l3-{prefix}-{pod}-egress-{other_pod}-{count}",
                                                             f"{prefix}-{vm}-{pod}",
                                                             f"{prefix}-{other_vm}-{other_pod}"))
                                count += 1
                                first = write_delimiter(out, first)
                                out.write(ingress_only.format(f"l3-{prefix}-{pod}-ingress-{other_pod}-{count}",
                                                              f"{prefix}-{other_vm}-{other_pod}",
                                                              f"{prefix}-{vm}-{pod}"))
                                count += 1

        while count < end:
            # For each VM
            for c1, vm in enumerate(vms):
                # For each Pod in the VM
                for p1, pod in enumerate(names[c1]):
                    first = write_delimiter(out, first)
                    out.write(egress_only.format(f"l3-{prefix}-{pod}-egress-null-{count}",
                                                 f"{prefix}-{vm}-{pod}",
                                                 f"{prefix}-null-{count}"))
                    count += 1
                    first = write_delimiter(out, first)
                    out.write(ingress_only.format(f"l3-{prefix}-{pod}-ingress-null-{count}",
                                                  f"{prefix}-null-{count}",
                                                  f"{prefix}-{vm}-{pod}"))
                    count += 1
                    if count >= end:
                        break;
                if count >= end:
                    break;


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(f"Usage: python3 {sys.argv[0]} <gen id> <pods.json> <output.yaml> <start> <end>")
    else:
        prefix = sys.argv[1]
        podfile = sys.argv[2]
        output = sys.argv[3]
        start = int(sys.argv[4])
        end = int(sys.argv[5])
        try:
            os.remove(output)
        except OSError:
            pass

        with open(podfile) as pf:
            scen = json.load(pf)
            policy_data = gen_policy(scen, output, prefix, start, end)
