#!/usr/bin/env bash
# Start the local ComfyUI container and report its final state.
# Verification:
#   bash -n scripts/start_comfyui.sh
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
start_timeout="${COMFYUI_START_TIMEOUT:-90}"

case "${start_timeout}" in
  ''|*[!0-9]*)
    printf 'COMFYUI_START_TIMEOUT must be an integer number of seconds\n' >&2
    exit 2
    ;;
esac

hostname_value="$(hostname 2>/dev/null || printf 'unknown')"
timestamp="$(date '+%Y-%m-%d %H:%M:%S %Z')"

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
  docker inspect \
    --format '{{.State.Status}}	{{if .State.Health}}{{.State.Health.Status}}{{else}}sem healthcheck{{end}}' \
    "${container_name}" 2>/dev/null || true
}

state_field() {
  printf '%s' "$1" | cut -f"$2"
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
  docker logs --tail 20 "${container_name}" 2>&1 || printf 'nao foi possivel ler os logs\n'
  close_block
}

print_final_state() {
  state="$(container_state)"
  status="$(state_field "${state}" 1)"
  health="$(state_field "${state}" 2)"

  print_section "📡 Estado Final"
  printf "%-10s %s\n" "Status" "${status:-inexistente}"
  printf "%-10s %s\n" "Saude" "${health:-desconhecida}"
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

if ! docker info >/dev/null 2>&1; then
  print_section "❌ Falha"
  printf "%-10s %s\n" "Docker" "daemon inacessivel para este usuario"
  printf "%s\n" "Verifique se o usuario do Hermes pertence ao grupo docker."
  close_block
  exit 1
fi

initial_state="$(container_state)"
initial_status="$(state_field "${initial_state}" 1)"

if [ "${initial_status}" = "running" ]; then
  print_section "ℹ️ Ja Estava no Ar"
  printf "%-10s %s\n" "Acao" "nenhuma; o container ja estava em execucao"
  close_block
  print_final_state
  exit 0
fi

print_gpu_snapshot

print_section "🚀 Start"
if [ -n "${initial_state}" ]; then
  printf "%-10s %s\n" "Acao" "docker start ${container_name}"
  if ! start_output="$(docker start "${container_name}" 2>&1)"; then
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
  if ! start_output="$(docker compose -f "${compose_file}" \
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

print_section "⏳ Aguardando Saude"
printf "%-10s %ss\n" "Limite" "${start_timeout}"
waited=0
final_status=""
final_health=""
while :; do
  state="$(container_state)"
  final_status="$(state_field "${state}" 1)"
  final_health="$(state_field "${state}" 2)"

  if [ "${final_health}" = "healthy" ]; then
    printf "%-10s %ss\n" "Pronto" "${waited}"
    break
  fi

  if [ "${final_health}" = "sem healthcheck" ] && [ "${final_status}" = "running" ]; then
    printf "%-10s %s\n" "Pronto" "container em execucao (sem healthcheck)"
    break
  fi

  if [ "${final_status}" != "running" ] && [ "${final_status}" != "restarting" ] && [ "${waited}" -gt 0 ]; then
    printf "%-10s %s\n" "Parou" "status ${final_status:-inexistente}"
    break
  fi

  if [ "${waited}" -ge "${start_timeout}" ]; then
    printf "%-10s %ss\n" "Timeout" "${waited}"
    break
  fi

  sleep 3
  waited=$((waited + 3))
done
close_block

print_final_state

if [ "${final_health}" = "healthy" ] ||
  { [ "${final_health}" = "sem healthcheck" ] && [ "${final_status}" = "running" ]; }; then
  print_section "✅ ComfyUI Disponivel"
  printf "%-10s %s\n" "Endereco" "${service_url}"
  close_block
  exit 0
fi

print_recent_logs
exit 1
