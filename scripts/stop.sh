#!/usr/bin/env bash

# 获取脚本所在目录
script_dir=$(cd $(dirname "$0") || exit 1; pwd)
work_dir=$(cd "${script_dir}"/.. || exit 1; pwd)
run_dir=${work_dir}/run
pid_file=${run_dir}/pid.txt

echo "Stopping RAG service..."

# 停止进程
if [ -f "${pid_file}" ]; then
  while read -r pid; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping process $pid"
      kill "$pid"
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        echo "Force stopping process $pid"
        kill -9 "$pid"
      fi
    fi
  done < "${pid_file}"
  rm -f "${pid_file}"
  echo "RAG service stopped."
else
  echo "No PID file found."
fi