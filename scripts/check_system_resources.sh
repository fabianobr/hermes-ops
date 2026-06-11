#!/usr/bin/env bash
# Verification:
#   bash scripts/check_system_resources.sh

set -eu

hostname_value="$(hostname 2>/dev/null || printf 'unknown')"
timestamp="$(date '+%Y-%m-%d %H:%M:%S %Z')"

bytes_to_gib() {
  awk -v bytes="$1" 'BEGIN { printf "%.1f GiB", bytes / 1024 / 1024 / 1024 }'
}

print_header_table() {
  echo "🧾 Status do Host"
  echo
  echo '```text'
  printf "%-10s %s\n" "Host" "${hostname_value}"
  printf "%-10s %s\n" "Hora" "${timestamp}"
  echo '```'
}

print_section() {
  echo
  echo "$1"
  echo
  echo '```text'
}

close_block() {
  echo '```'
}

print_nvidia_gpu() {
  print_section "🎮 GPU / VRAM"

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    printf "%-10s %s\n" "NVIDIA" "nvidia-smi nao encontrado"
    close_block
    return
  fi

  if ! nvidia-smi -L >/dev/null 2>&1; then
    printf "%-10s %s\n" "NVIDIA" "nvidia-smi presente, mas nenhuma GPU disponivel"
    close_block
    return
  fi

  nvidia-smi \
    --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit \
    --format=csv,noheader,nounits |
    while IFS=',' read -r index name gpu_util mem_used mem_total temp power_draw power_limit; do
      index="$(printf '%s' "$index" | xargs)"
      name="$(printf '%s' "$name" | xargs)"
      gpu_util="$(printf '%s' "$gpu_util" | xargs)"
      mem_used="$(printf '%s' "$mem_used" | xargs)"
      mem_total="$(printf '%s' "$mem_total" | xargs)"
      temp="$(printf '%s' "$temp" | xargs)"
      power_draw="$(printf '%s' "$power_draw" | xargs)"
      power_limit="$(printf '%s' "$power_limit" | xargs)"

      echo "${index}: ${name}"
      printf "%-10s %s%%\n" "Uso" "${gpu_util}"
      printf "%-10s %s / %s MiB\n" "VRAM" "${mem_used}" "${mem_total}"
      printf "%-10s %s C\n" "Temp" "${temp}"
      printf "%-10s %s / %s W\n" "Power" "${power_draw}" "${power_limit}"
    done
  close_block
}

print_resources() {
  load_average="$(awk '{print $1 ", " $2 ", " $3}' /proc/loadavg)"
  cpu_cores="$(nproc 2>/dev/null || printf 'unknown')"
  cpu_usage="indisponivel"

  if command -v mpstat >/dev/null 2>&1; then
    cpu_usage="$(mpstat 1 1 | awk '/Average:/ && $2 == "all" { printf "%.1f%%", 100 - $NF }')"
  fi

  if command -v free >/dev/null 2>&1; then
    ram_summary="$(free -h | awk '/^Mem:/ { print $3 " / " $2 " usados, " $7 " livre" }')"
    swap_summary="$(free -h | awk '/^Swap:/ { print $3 " / " $2 " usados" }')"
  else
    mem_total="$(awk '/MemTotal:/ {print $2 * 1024}' /proc/meminfo)"
    mem_available="$(awk '/MemAvailable:/ {print $2 * 1024}' /proc/meminfo)"
    mem_used="$((mem_total - mem_available))"
    ram_summary="$(bytes_to_gib "$mem_used") / $(bytes_to_gib "$mem_total") usados"
    swap_summary="indisponivel"
  fi

  disk_summary="$(df -h / | awk 'NR == 2 { print $3 " / " $2 " usados (" $5 ")" }')"

  print_section "⚙️ CPU / RAM / Disco"
  printf "%-10s %s\n" "CPU load" "${load_average}"
  printf "%-10s %s\n" "CPU cores" "${cpu_cores}"
  printf "%-10s %s\n" "CPU uso" "${cpu_usage}"
  printf "%-10s %s\n" "RAM" "${ram_summary}"
  printf "%-10s %s\n" "Swap" "${swap_summary}"
  printf "%-10s %s\n" "Disco /" "${disk_summary}"
  close_block
}

print_top_processes() {
  print_section "📦 Top Processos por RAM"
  printf "%-18s %7s %7s %7s %10s\n" "Processo" "PID" "CPU" "MEM" "RSS"
  ps -eo comm,pid,%cpu,%mem,rss --sort=-rss |
    awk 'NR > 1 && NR <= 6 { printf "%-18s %7s %6s%% %6s%% %9.1fM\n", $1, $2, $3, $4, $5 / 1024 }' 2>/dev/null
  close_block
}

print_header_table
print_nvidia_gpu
print_resources
print_top_processes
