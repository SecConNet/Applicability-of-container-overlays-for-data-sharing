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
import numpy as np

vms = ["ovr-0", "ovr-1"]

# This is a template pod definition.
pod_template = "\
{{ \"VMs\": [{}],\n\
  \"VMpodnames\": [{}]\n\
}}\n\
"

test = "{}, {}"


def gen_pods_json(output, prefix, start, end):
    """
    Loop over all combinations of pods and write l4 policies for the
    combinations to 'output'.
    When the range from start till end is bigger than the number of pod
    combinations or when start doesn't equal 0, then l3 rules are made between
    existing pods and non-exsisting pods.

    (Yes this function is very ugly, I know, but I was lazy)
    """
    names = {}
    for vm in vms:
        names[vm] = ""

    first = True
    count = start
    n = len(vms)
    back = start % int(np.math.factorial(n) / np.math.factorial(n - 2))
    count -= back
    with open(output, 'a') as out:
        # For each possible VM combination
        while count < end:
            for c1, vm in enumerate(vms):
                for c2, other_vm in enumerate(vms):
                    if c1 != c2:
                        if count < start:
                            count += 1
                            continue

                        name_c = f"{count}-client"
                        name_s = f"{count}-server"
                        names[vm] += f"\"{name_c}\", "
                        names[other_vm] += f"\"{name_s}\", "
                        count += 1
                    if count >= end:
                        break;
                if count >= end:
                    break;

        vm_string = ""
        pod_string = ""
        for vm, pods in names.items():
            vm_string += f"\"{vm}\", "
            pod_string += f"[{pods[:-2]}], "

        out.write(pod_template.format(vm_string[:-2], pod_string[:-2]))


if __name__ == "__main__":
    import subprocess
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <gen id> <output.yaml> <start> <end>")
    else:
        prefix = sys.argv[1]
        output = sys.argv[2]
        start = int(sys.argv[3])
        end = int(sys.argv[4])
        try:
            os.remove(output)
        except OSError:
            pass

        # with open(podfile) as pf:
        #     scen = json.load(pf)

        gen_pods_json("pod_scaling_tmp.json", prefix, start, end)
        subprocess.call(["python3", "pod_scaling/gen_pods.py",
                         prefix, "pod_scaling_tmp.json", output])
        subprocess.call(["rm", "pod_scaling_tmp.json"])
