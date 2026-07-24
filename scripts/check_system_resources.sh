#!/usr/bin/env bash
# Verification:
#   bash scripts/check_system_resources.sh
#   CHECK_SYSTEM_DISK_ALERT_THRESHOLD=0 bash scripts/check_system_resources.sh

set -eu

hostname_value="$(hostname 2>/dev/null || printf 'unknown')"
timestamp="$(date '+%Y-%m-%d %H:%M:%S %Z')"
disk_alert_threshold="${CHECK_SYSTEM_DISK_ALERT_THRESHOLD:-85}"

case "${disk_alert_threshold}" in
  ''|*[!0-9]*)
    printf 'CHECK_SYSTEM_DISK_ALERT_THRESHOLD must be an integer from 0 to 100\n' >&2
    exit 2
    ;;
esac

if [ "${disk_alert_threshold}" -gt 100 ]; then
  printf 'CHECK_SYSTEM_DISK_ALERT_THRESHOLD must be an integer from 0 to 100\n' >&2
  exit 2
fi

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

  gpu_rows="$(nvidia-smi \
    --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit \
    --format=csv,noheader,nounits 2>/dev/null || true)"

  if [ -z "${gpu_rows}" ]; then
    printf "%-10s %s\n" "NVIDIA" "nao foi possivel consultar a telemetria da GPU"
    close_block
    return
  fi

  printf '%s\n' "${gpu_rows}" |
    while IFS=',' read -r index name gpu_util mem_used mem_total temp power_draw power_limit; do
      index="$(printf '%s' "$index" | xargs)"
      name="$(printf '%s' "$name" | xargs)"
      gpu_util="$(printf '%s' "$gpu_util" | xargs)"
      mem_used="$(printf '%s' "$mem_used" | xargs)"
      mem_total="$(printf '%s' "$mem_total" | xargs)"
      temp="$(printf '%s' "$temp" | xargs)"
      power_draw="$(printf '%s' "$power_draw" | xargs)"
      power_limit="$(printf '%s' "$power_limit" | xargs)"
      gpu_util_display="$(awk -v value="${gpu_util}" 'BEGIN {
        if (value ~ /^[0-9]+([.][0-9]+)?$/) printf "%s%%", value
        else print "indisponivel"
      }')"
      vram_util_display="$(awk -v used="${mem_used}" -v total="${mem_total}" 'BEGIN {
        if (used ~ /^[0-9]+([.][0-9]+)?$/ && total ~ /^[0-9]+([.][0-9]+)?$/ && total > 0) {
          printf "%.1f%%", (used / total) * 100
        } else {
          print "indisponivel"
        }
      }')"

      echo "${index}: ${name}"
      printf "%-10s %s\n" "Uso GPU" "${gpu_util_display}"
      printf "%-10s %s / %s MiB\n" "VRAM" "${mem_used}" "${mem_total}"
      printf "%-10s %s\n" "Uso VRAM" "${vram_util_display}"
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
    cpu_usage="$(LC_ALL=C mpstat 1 1 | awk '/Average:/ && $2 == "all" { printf "%.1f%%", 100 - $NF }')"
    cpu_usage="${cpu_usage:-indisponivel}"
  fi

  if command -v free >/dev/null 2>&1; then
    ram_summary="$(free -h | awk '/^Mem:/ { print $3 " / " $2 " usados, " $7 " disponivel" }')"
    swap_summary="$(free -h | awk '/^Swap:/ { print $3 " / " $2 " usados" }')"
  else
    mem_total="$(awk '/MemTotal:/ {print $2 * 1024}' /proc/meminfo)"
    mem_available="$(awk '/MemAvailable:/ {print $2 * 1024}' /proc/meminfo)"
    mem_used="$((mem_total - mem_available))"
    ram_summary="$(bytes_to_gib "$mem_used") / $(bytes_to_gib "$mem_total") usados"
    swap_summary="indisponivel"
  fi

  disk_summary="$(df -hP / | awk 'NR == 2 { print $3 " / " $2 " usados (" $5 ")" }')"
  disk_used_percent="$(df -P / | awk 'NR == 2 { value=$5; gsub(/%/, "", value); print value }')"

  print_section "⚙️ CPU / RAM / Disco"
  printf "%-10s %s\n" "CPU load" "${load_average}"
  printf "%-10s %s\n" "CPU cores" "${cpu_cores}"
  printf "%-10s %s\n" "CPU uso" "${cpu_usage}"
  printf "%-10s %s\n" "RAM" "${ram_summary}"
  printf "%-10s %s\n" "Swap" "${swap_summary}"
  printf "%-10s %s\n" "Disco /" "${disk_summary}"
  close_block

  if [ "${disk_used_percent:-0}" -ge "${disk_alert_threshold}" ]; then
    print_section "⚠️ Pressao de Disco"
    printf "%-10s %s\n" "Disco /" "${disk_used_percent}% usado"
    printf "%-10s %s\n" "Acao" "investigacao somente leitura recomendada"
    close_block
  fi
}

describe_ollama_models() {
  awk '
    function trim(value) {
      sub(/^[[:space:]]+/, "", value)
      sub(/[[:space:]]+$/, "", value)
      return value
    }

    NR == 1 {
      id_column = index($0, "ID")
      size_column = index($0, "SIZE")
      processor_column = index($0, "PROCESSOR")
      context_column = index($0, "CONTEXT")
      until_column = index($0, "UNTIL")
      header_valid = id_column > 1 &&
        size_column > id_column &&
        processor_column > size_column &&
        context_column > processor_column &&
        until_column > context_column
      next
    }

    NF && header_valid {
      model_count++
      model_name[model_count] = trim(substr($0, 1, id_column - 1))
      model_id[model_count] = trim(substr($0, id_column, size_column - id_column))
      model_size[model_count] = trim(substr($0, size_column, processor_column - size_column))
      model_processor[model_count] = trim(substr($0, processor_column, context_column - processor_column))
      model_context[model_count] = trim(substr($0, context_column, until_column - context_column))
      model_until[model_count] = trim(substr($0, until_column))
    }

    END {
      if (!header_valid) {
        exit 2
      }

      printf "%-10s %d\n", "Modelos", model_count
      if (model_count == 0) {
        printf "%-10s %s\n", "Estado", "nenhum modelo carregado"
      }

      for (model_index = 1; model_index <= model_count; model_index++) {
        if (model_index > 1) {
          print ""
        }
        printf "%-10s %s\n", "Modelo", model_name[model_index]
        printf "%-10s %s\n", "ID", model_id[model_index]
        printf "%-10s %s\n", "Memoria", model_size[model_index]
        printf "%-10s %s\n", "CPU/GPU", model_processor[model_index]
        printf "%-10s %s tokens\n", "Contexto", model_context[model_index]
        printf "%-10s %s\n", "Ate", model_until[model_index]
      }
    }
  '
}

print_ollama_status() {
  print_section "🧠 Ollama em Execucao"

  ollama_command="$(command -v ollama 2>/dev/null || true)"
  if [ -z "${ollama_command}" ]; then
    # systemd services commonly omit /snap/bin from PATH.
    for ollama_candidate in /snap/bin/ollama /usr/local/bin/ollama /usr/bin/ollama; do
      if [ -x "${ollama_candidate}" ]; then
        ollama_command="${ollama_candidate}"
        break
      fi
    done
  fi

  if [ -z "${ollama_command}" ]; then
    printf "%-10s %s\n" "Ollama" "comando nao encontrado"
    close_block
    return
  fi

  if command -v timeout >/dev/null 2>&1; then
    if ollama_output="$(timeout 5s "${ollama_command}" ps 2>&1)"; then
      :
    else
      ollama_status=$?
      printf "%-10s %s\n" "Ollama" "ollama ps falhou (status ${ollama_status})"
      [ -n "${ollama_output}" ] && printf '%s\n' "${ollama_output}"
      close_block
      return
    fi
  elif ollama_output="$("${ollama_command}" ps 2>&1)"; then
    :
  else
    ollama_status=$?
    printf "%-10s %s\n" "Ollama" "ollama ps falhou (status ${ollama_status})"
    [ -n "${ollama_output}" ] && printf '%s\n' "${ollama_output}"
    close_block
    return
  fi

  if [ -n "${ollama_output}" ]; then
    if ollama_description="$(printf '%s\n' "${ollama_output}" | describe_ollama_models)"; then
      printf '%s\n' "${ollama_description}"
    else
      printf "%-10s %s\n" "Ollama" "formato de ollama ps nao reconhecido"
      printf '%s\n' "${ollama_output}"
    fi
  else
    printf "%-10s %s\n" "Ollama" "ollama ps nao retornou dados"
  fi
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
print_ollama_status
print_top_processes
