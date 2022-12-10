"""
For a given json file which defines pods that should be launched on
some nodes, this script creates yaml files which can spawn these pods.
"""

import json
import sys
import os

# Template for the pod yaml file.
pod_template = "\
apiVersion: v1\n\
kind: Pod\n\
metadata:\n\
  name: {}\n\
  labels: {{\n\
    id.pod: {},\n\
  }}\n\
spec:\n\
  nodeName: {}\n\
  volumes:\n\
  - name: results-volume\n\
    hostPath:\n\
      path: /home/niek/results\n\
      type: Directory\n\
  containers:\n\
  - name: ubuntu-shell\n\
    image: ubuntu-shell\n\
    stdin: true\n\
    tty: true\n\
    imagePullPolicy: IfNotPresent\n\
    volumeMounts:\n\
    - name: results-volume\n\
      mountPath: /usr/share/results\n\
    securityContext:\n\
      privileged: true\n\
"

def gen_pods(scen, output, prefix):
    """
    Write the pods to the output file using the template.
    """
    vms = scen["VMs"]
    names = scen["VMpodnames"]
    first = True

    with open(output, 'a') as out:
        for c, vm in enumerate(vms):
            for pod in names[c]:
                name = prefix + "-" + pod
                if not first:
                    out.write("---\n")
                else:
                    first = False

                out.write(pod_template.format(name, name, vm))

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 gen_pods.py <gen id> <pods.json> <output.yaml>")
    else:
        prefix = sys.argv[1]
        file = sys.argv[2]
        output = sys.argv[3]
        try:
            os.remove(output)
        except OSError:
            pass

        with open(file) as f:
            scen = json.load(f)
            policy_data = gen_pods(scen, output, prefix)
