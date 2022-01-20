#!/bin/bash
shopt -s extglob

YAMLS=(1 2 3 4 5 6 7 8 9 10 20 30 40 50 60 70 80 90 100)
# YAMLS=(1 2 3)
VMS=("ovr-0" "ovr-1")
VM_COUNT="${#VMS[@]}"


name_to_ip() {
  local name=$1
  local IFS=$'\n'
  IP="$(kubectl describe pods "$name" | grep IP:)"
  echo "${IP##* }"
}

cilium_agents() {
  echo "$(kubectl get pods -l k8s-app=cilium -n kube-system | cut -d$' ' -f 1 | tail -n +2)"
}

podname_to_vm() {
  local podname=$1
  local vm_name=$(kubectl get pod -o=custom-columns=NODE:.spec.nodeName,NAME:.metadata.name --all-namespaces | grep $podname | cut -d' ' -f1)
  echo "$vm_name"
}

vm_to_cilium_agent() {
  local vm_name=$1
  local agent=$(kubectl get pods -o=custom-columns=NAME:.metadata.name,NODE:.spec.nodeName -l k8s-app=cilium -n kube-system | grep $vm_name | cut -d' ' -f1)
  echo "$agent"
}

podname_to_cilium_agent() {
  local podname=$1
  local vm_name=$(podname_to_vm $podname)
  local agent=$(vm_to_cilium_agent $vm_name)
  echo "$agent"
}

# query_pods() {
#   local pod=""
#   local pods=""
#   local agent=""
#   for vm in ${VMS[@]}; do
#     agent=$(vm_to_cilium_agent $vm)
#     pod=$(kubectl -n kube-system exec -it $agent -- cilium metrics list | grep cilium_endpoint_count)
#     pod="${pod##* }"
#     pods="$pods${pod%%.*} "
#   done
#
#   echo "$pods"
# }

# poll_pods() {
#   local needed=$(( $1 * 2 * ($VM_COUNT - 1) ))
#   local count=""
#   local bool=1
#   local pods=""
#   local initial=($INITIAL_POD_COUNTS)
#   local filtered=""
#   while [[ $bool != 0 ]]; do
#     pods=($(query_pods))
#     for i in "${!initial[@]}"; do
#       filtered="$filtered$(( ${pods[$i]} - ${initial[$i]} )) "
#     done
#
#     echo "Polled Cilium agents, endpoint_count (need: $needed): $filtered"
#     bool=0
#     for pol_count in $filtered; do
#       if [[ "$pol_count" -lt "$needed" ]]; then
#         bool=1
#       fi
#     done
#
#     if [[ $bool != 0 ]]; then
#       filtered=""
#       sleep 1
#     fi
#   done
# }

unready_pods() {
  local readys=$(kubectl get pod -o=custom-columns=READY:.status.conditions[1].status | tail -n +2)
  local count=0
  for ready in $readys; do
    if [[ $ready != "True" ]]; then
      count=$(( $count + 1 ))
    fi
  done

  echo "$count"
}

poll_pods() {
  local count=1
  while [[ $count != 0 ]]; do
    sleep 5
    count=$(unready_pods)
    echo "Number of Pods not Ready: $count"
  done
}

clean() {
  local name_client=$1
  echo "Cleaning Results..."
  for m in "${MODES[@]}"; do
    kubectl exec "$name_client" -- /bin/bash -c "./scripts/clean_dirs.sh /usr/share/results/$RESULT_DIR-$m"
  done
}

clean_vms() {
  local client=""
  for vm in ${VMS[@]}; do
    client=$(kubectl get pods -o=custom-columns=NAME:.metadata.name,NODE:.spec.nodeName | grep -E "client *$vm" | head -n 1 | cut -d' ' -f1)
    echo "[$vm] Clean Slave: $client"
    clean "$client"

    local y=""
    for y in "${YAMLS[@]}"; do
      for m in "${MODES[@]}"; do
        kubectl exec "$client" -- /bin/bash -c "mkdir /usr/share/results/$RESULT_DIR-$m/pods$y-client"
        kubectl exec "$client" -- /bin/bash -c "mkdir /usr/share/results/$RESULT_DIR-$m/pods$y-server"
      done
    done
  done
}

start_server() {
  local duo=$1
  local name_server="duo-$duo-server"
  local ip_server=$(name_to_ip "$name_server")
  local duo_iperf_file="duo-$duo-iperf.json"
  local tmp="tmp$duo.json"

  echo "[duo-$duo] Starting Server: $name_server ($ip_server)"
  kubectl exec "$name_server" -- /bin/bash -c "./scripts/iperf_server.sh $PORT $CURRENT_DIR-server/$tmp" &
  sleep 1
}

start_cpu() {
  local duo=$1
  local name_client="duo-$duo-client"
  local name_server="duo-$duo-server"
  local duo_cpu_file="duo-$duo-cpu.txt"
  echo "[duo-$duo] Starting CPU monitors..."
  kubectl exec "$name_server" -- /bin/bash -c "./scripts/cpu_usage.sh $CURRENT_DIR-server/$duo_cpu_file 0.1" &
  kubectl exec "$name_client" -- /bin/bash -c "./scripts/cpu_usage.sh $CURRENT_DIR-client/$duo_cpu_file 0.1" &
}

start_client() {
  local duo=$1
  local name_server="duo-$duo-server"
  local name_client="duo-$duo-client"
  local ip_server=$(name_to_ip "$name_server")
  local ip_client=$(name_to_ip "$name_client")
  local duo_iperf_file="duo-$duo-iperf.json"
  local tmp="tmp$duo.json"

  echo "[duo-$duo] Starting Client: $name_client ($ip_client)"
  kubectl exec "$name_client" -- /bin/bash -c "./scripts/iperf_client.sh $ip_server $PORT $CURRENT_DIR-client/$duo_iperf_file $TIME $m $BANDWIDTH $SIZE"
  echo "[duo-$duo] Client done, killing Server and CPU monitors..."
  kubectl exec "$name_server" -- /bin/bash -c "pkill iperf3"
  kubectl exec "$name_server" -- /bin/bash -c "pkill cpu_usage.sh"
  kubectl exec "$name_client" -- /bin/bash -c "pkill cpu_usage.sh"
  echo "[duo-$duo] Terminating..."
  sleep 2

  kubectl exec "$name_server" -- /bin/bash -c "head -n -11 $CURRENT_DIR-server/$tmp > $CURRENT_DIR-server/$duo_iperf_file"
  kubectl exec "$name_server" -- /bin/bash -c "rm $CURRENT_DIR-server/$tmp"
  echo "[duo-$duo] Done!"
}

experiment() {
  RESULT_DIR=$1
  TIME=$2
  PORT=$3
  local mode=$4
  SIZE=""
  BANDWIDTH=""
  NEWLINE=$'\n'
  if [[ $mode == "udp" ]]; then
    MODES=(udp)
  elif [[ $mode == "tcp" ]]; then
    MODES=(tcp)
  elif [[ $mode == "both" ]]; then
    MODES=(tcp udp)
  else
    echo "Invalid mode, possible values: tcp, udp, both"
    exit 1
  fi

  # INITIAL_POD_COUNTS=$(query_pods)
  # echo "Initial Pod Counts: $INITIAL_POD_COUNTS"
  local yaml=""
  local first=1
  local y=""
  for y in "${YAMLS[@]}"; do
    echo "${newline}${NEWLINE}${NEWLINE}Experiment Pod Count: $y"
    yaml="n2_scaling_pods-$y.yaml"
    echo "Apply: $yaml"
    kubectl create -f "yamls/$yaml"
    sleep 1
    poll_pods

# If this is the first iteration, clean the result directories of the VMs
    if [[ $first == 1 ]]; then
      first=0
      clean_vms
    fi

    for m in "${MODES[@]}"; do
      if [[ $m == "udp" ]]; then
        SIZE=""
        BANDWIDTH="0"
      else
        SIZE=""
        BANDWIDTH=""
      fi

      CURRENT_DIR="/usr/share/results/$RESULT_DIR-$m/pods$y"
      echo "${NEWLINE}Begin $m experiment. $y"
      for duo in $(seq 0 $(($y * 2 - 1))); do
        start_server "$duo" &
      done
      wait

      for duo in $(seq 0 $(($y * 2 - 1))); do
        start_cpu "$duo" &
      done
      wait

      for duo in $(seq 0 $(($y * 2 - 1))); do
        start_client "$duo" &
      done
      wait
    done
  done
}

if [[ $# -lt "4" ]]; then
  echo "Usage: $0 <result dir> <time> <port> <tcp/udp/both>"
  exit 1
else
  experiment "$1" "$2" "$3" "$4"
fi
