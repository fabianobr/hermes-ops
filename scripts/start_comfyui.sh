#!/usr/bin/env bash
# Start the local ComfyUI container and report its final state.
# Verification:
#   bash -n scripts/start_comfyui.sh
#   python3 -m unittest tests.test_start_comfyui
#   bash scripts/start_comfyui.sh
#   COMFYUI_START_TIMEOUT=30 bash scripts/start_comfyui.sh

set -eu

if [ "$#" -ne 0 ]; then
  printf 'start_comfyui.sh does not accept arguments\n' >&2
  exit 2
fi

container_name="${COMFYUI_CONTAINER:-comfyui}"
compose_file="${COMFYUI_COMPOSE_FILE:-${HOME}/homelab-ai/infra/docker/docker-compose.yml}"
compose_profile="${COMFYUI_COMPOSE_PROFILE:-media-pipeline}"
compose_service="${COMFYUI_COMPOSE_SERVICE:-comfyui}"
service_url="${COMFYUI_URL:-http://127.0.0.1:8188}"
probe_path="${COMFYUI_PROBE_PATH:-/system_stats}"
start_timeout="${COMFYUI_START_TIMEOUT:-120}"
poll_interval="${COMFYUI_POLL_INTERVAL:-3}"

require_integer() {
  case "$2" in
    ''|*[!0-9]*)
      printf '%s must be an integer number of seconds\n' "$1" >&2
      exit 2
      ;;
  esac
}

require_integer COMFYUI_START_TIMEOUT "${start_timeout}"
require_integer COMFYUI_POLL_INTERVAL "${poll_interval}"

if [ "${poll_interval}" -lt 1 ]; then
  poll_interval=1
fi

hostname_value="$(hostname 2>/dev/null || printf 'unknown')"
timestamp="$(date '+%Y-%m-%d %H:%M:%S %Z')"

have_timeout=0
if command -v timeout >/dev/null 2>&1; then
  have_timeout=1
fi

# Every docker call is bounded. A wedged daemon can accept the socket
# connection and never answer, which would otherwise hang the Telegram quick
# command with no output at all.
run_docker() {
  docker_budget="$1"
  shift
  if [ "${have_timeout}" = "1" ]; then
    timeout "${docker_budget}s" docker "$@"
  else
    docker "$@"
  fi
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

print_header_table() {
  echo "🎨 Iniciar ComfyUI"
  echo
  echo '```text'
  printf "%-10s %s\n" "Host" "${hostname_value}"
  printf "%-10s %s\n" "Hora" "${timestamp}"
  printf "%-10s %s\n" "Container" "${container_name}"
  echo '```'
}

# Prints "status<TAB>health" for the container, or nothing when it is absent.
container_state() {
  run_docker 10 inspect \
    --format '{{.State.Status}}	{{if .State.Health}}{{.State.Health.Status}}{{else}}sem healthcheck{{end}}' \
    "${container_name}" 2>/dev/null || true
}

state_field() {
  printf '%s' "$1" | cut -f"$2"
}

probe_tool=""
if command -v curl >/dev/null 2>&1; then
  probe_tool="curl"
elif command -v python3 >/dev/null 2>&1; then
  probe_tool="python3"
fi

# Asking the service directly is what the operator actually cares about, and it
# answers within seconds instead of waiting out the container health interval.
probe_service() {
  case "${probe_tool}" in
    curl)
      curl -fsS --max-time 5 -o /dev/null "${service_url}${probe_path}" 2>/dev/null
      ;;
    python3)
      python3 - "${service_url}${probe_path}" <<'PROBE' 2>/dev/null
import sys
import urllib.request

try:
    urllib.request.urlopen(sys.argv[1], timeout=5).read()
except Exception:
    sys.exit(1)
PROBE
      ;;
    *)
      return 1
      ;;
  esac
}

container_ready() {
  ready_status="$1"
  ready_health="$2"

  [ "${ready_status}" = "running" ] || return 1
  [ "${ready_health}" = "healthy" ] && return 0

  if probe_service; then
    return 0
  fi

  # With no healthcheck and no way to probe, "running" is all the evidence
  # available.
  if [ "${ready_health}" = "sem healthcheck" ] && [ -z "${probe_tool}" ]; then
    return 0
  fi

  return 1
}

print_gpu_snapshot() {
  print_section "🎮 VRAM Antes do Start"

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    printf "%-10s %s\n" "NVIDIA" "nvidia-smi nao encontrado"
    close_block
    return
  fi

  gpu_rows="$(nvidia-smi \
    --query-gpu=index,name,memory.used,memory.total \
    --format=csv,noheader,nounits 2>/dev/null || true)"

  if [ -z "${gpu_rows}" ]; then
    printf "%-10s %s\n" "NVIDIA" "nao foi possivel consultar a telemetria da GPU"
    close_block
    return
  fi

  printf '%s\n' "${gpu_rows}" |
    while IFS=',' read -r index name mem_used mem_total; do
      index="$(printf '%s' "${index}" | xargs)"
      name="$(printf '%s' "${name}" | xargs)"
      mem_used="$(printf '%s' "${mem_used}" | xargs)"
      mem_total="$(printf '%s' "${mem_total}" | xargs)"
      printf "%s: %s\n" "${index}" "${name}"
      printf "%-10s %s / %s MiB\n" "VRAM" "${mem_used}" "${mem_total}"
      awk -v used="${mem_used}" -v total="${mem_total}" 'BEGIN {
        if (total + 0 > 0) {
          printf "%-10s %s MiB\n", "Livre", total - used
          if ((total - used) < 4096) {
            printf "%-10s %s\n", "Atencao", "pouca VRAM livre; a GPU e compartilhada com o Ollama"
          }
        }
      }'
    done
  close_block
}

print_recent_logs() {
  print_section "🪵 Ultimas Linhas de Log"
  run_docker 15 logs --tail 20 "${container_name}" 2>&1 ||
    printf 'nao foi possivel ler os logs\n'
  close_block
}

# Takes the state the caller already observed, so the report can never
# contradict the exit code it is printed next to.
print_final_state() {
  print_section "📡 Estado Final"
  printf "%-10s %s\n" "Status" "${1:-inexistente}"
  printf "%-10s %s\n" "Saude" "${2:-desconhecida}"
  printf "%-10s %s\n" "Endereco" "${service_url}"
  close_block
}

print_header_table

if ! command -v docker >/dev/null 2>&1; then
  print_section "❌ Falha"
  printf "%-10s %s\n" "Docker" "comando docker nao encontrado"
  close_block
  exit 1
fi

if ! run_docker 10 info >/dev/null 2>&1; then
  print_section "❌ Falha"
  printf "%-10s %s\n" "Docker" "daemon inacessivel ou sem resposta"
  printf "%s\n" "Verifique se o usuario do Hermes pertence ao grupo docker."
  close_block
  exit 1
fi

initial_state="$(container_state)"
initial_status="$(state_field "${initial_state}" 1)"
initial_health="$(state_field "${initial_state}" 2)"

if [ "${initial_status}" = "running" ] && container_ready "${initial_status}" "${initial_health}"; then
  print_section "ℹ️ Ja Estava no Ar"
  printf "%-10s %s\n" "Acao" "nenhuma; o container ja estava respondendo"
  close_block
  print_final_state "${initial_status}" "${initial_health}"
  exit 0
fi

if [ "${initial_status}" = "running" ]; then
  # Running but not answering yet: skip the start and wait it out instead of
  # reporting a success the service cannot back.
  print_section "⚠️ Em Execucao Sem Responder"
  printf "%-10s %s\n" "Status" "${initial_status}"
  printf "%-10s %s\n" "Saude" "${initial_health:-desconhecida}"
  printf "%-10s %s\n" "Acao" "nenhuma; aguardando o servico responder"
  close_block
else
  print_gpu_snapshot

  print_section "🚀 Start"
  if [ -n "${initial_state}" ]; then
    printf "%-10s %s\n" "Acao" "docker start ${container_name}"
    if ! start_output="$(run_docker 60 start "${container_name}" 2>&1)"; then
      printf "%-10s %s\n" "Resultado" "falhou"
      printf '%s\n' "${start_output}"
      close_block
      print_recent_logs
      exit 1
    fi
  elif [ -f "${compose_file}" ]; then
    printf "%-10s %s\n" "Acao" "docker compose up -d --no-build ${compose_service}"
    printf "%-10s %s\n" "Arquivo" "${compose_file}"
    # --no-build keeps a missing image an explicit operator decision instead of
    # triggering a long unattended build from a Telegram command.
    if ! start_output="$(run_docker 180 compose -f "${compose_file}" \
      --profile "${compose_profile}" up -d --no-build "${compose_service}" 2>&1)"; then
      printf "%-10s %s\n" "Resultado" "falhou"
      printf '%s\n' "${start_output}"
      printf "%s\n" "Se a imagem ainda nao existe, faca o build manualmente no host."
      close_block
      exit 1
    fi
  else
    printf "%-10s %s\n" "Resultado" "falhou"
    printf "%-10s %s\n" "Container" "inexistente"
    printf "%-10s %s\n" "Compose" "${compose_file} nao encontrado"
    close_block
    exit 1
  fi
  printf "%-10s %s\n" "Resultado" "comando aceito"
  close_block
fi

print_section "⏳ Aguardando Resposta"
printf "%-10s %ss\n" "Limite" "${start_timeout}"
waited=0
final_status=""
final_health=""
ready=0
while :; do
  state="$(container_state)"
  final_status="$(state_field "${state}" 1)"
  final_health="$(state_field "${state}" 2)"

  if container_ready "${final_status}" "${final_health}"; then
    ready=1
    printf "%-10s %ss\n" "Pronto" "${waited}"
    break
  fi

  if [ "${final_status}" != "running" ] && [ "${final_status}" != "restarting" ] &&
    [ "${waited}" -gt 0 ]; then
    printf "%-10s %s\n" "Parou" "status ${final_status:-inexistente}"
    break
  fi

  if [ "${waited}" -ge "${start_timeout}" ]; then
    printf "%-10s %ss\n" "Timeout" "${waited}"
    break
  fi

  sleep "${poll_interval}"
  waited=$((waited + poll_interval))
done
close_block

print_final_state "${final_status}" "${final_health}"

if [ "${ready}" = "1" ]; then
  print_section "✅ ComfyUI Disponivel"
  printf "%-10s %s\n" "Endereco" "${service_url}"
  close_block
  exit 0
fi

print_recent_logs
exit 1
