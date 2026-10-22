#!/usr/bin/env bash
# ==============================================================================
# StackLabs Platform: Clio Headless Agent Execution Runner (Pure GitOps)
# Path: /home/james/stacklabs/scripts/clio_agent_exec.sh
# Usage: clio_agent_exec.sh --ticket <path-to-ticket.md> [--workspace <path>]
# ==============================================================================
set -euo pipefail

WORKSPACE_DIR="/home/james/stacklabs"
QUEUE_DIR="/home/james/stacklabs/queue"
LOG_DIR="${QUEUE_DIR}/logs"
NOTIFY_BIN="/home/james/stacklabs/scripts/clio-notify.sh"
AGY_BIN="/home/james/.local/bin/agy"

mkdir -p "${LOG_DIR}"

usage() {
  echo "Usage: $0 --ticket <path-to-ticket.md> [--workspace <path>]"
  exit 1
}

TICKET_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ticket)
      TICKET_PATH="$2"
      shift 2
      ;;
    --workspace)
      WORKSPACE_DIR="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

if [[ -z "${TICKET_PATH}" || ! -f "${TICKET_PATH}" ]]; then
  echo "[ERROR] Invalid or missing ticket file: ${TICKET_PATH}" >&2
  usage
fi

TICKET_NAME=$(basename "${TICKET_PATH}" .md)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_LOG="${LOG_DIR}/${TICKET_NAME}_${TIMESTAMP}.log"
CURRENT_LOG="${LOG_DIR}/current.log"

# Maintain current.log symlink for HUD streaming
ln -sf "${RUN_LOG}" "${CURRENT_LOG}"

echo "==================================================" | tee -a "${RUN_LOG}"
echo "⚡ CLIO AGENT EXECUTION RUNNER — PURE GITOPS AGY" | tee -a "${RUN_LOG}"
echo "Ticket:    ${TICKET_PATH}" | tee -a "${RUN_LOG}"
echo "Workspace: ${WORKSPACE_DIR}" | tee -a "${RUN_LOG}"
echo "Timestamp: ${TIMESTAMP}" | tee -a "${RUN_LOG}"
echo "==================================================" | tee -a "${RUN_LOG}"

# Build the system instruction envelope wrapping the ticket contents
SYSTEM_DIRECTIVE="You are Clio, Forge Master and Autonomous Execution Worker on host clio.
You have full code read/write, terminal privileges, and own the metal.
Your mandate:
1. Parse the requirements, acceptance criteria, and target files in the ticket below.
2. Implement required code changes, database migrations, or configuration updates.
3. Run verification tests and production builds specified in Quarter 3/4.
4. Generate the canonical walkthrough report at /home/james/stacklabs/walkthroughs/walkthrough_${TICKET_NAME}.md.
5. Exit cleanly with a concise summary.

GitOps Execution Rules:
- All operations are tracked via Markdown files on disk (Queue, Walkthroughs, Code).
- Do NOT waste time inserting internal tracking rows into SQLite ticketing databases.
- Do NOT recursively grep through models/, node_modules/, or .venv/."

PROMPT_PAYLOAD=$(cat <<EOF
${SYSTEM_DIRECTIVE}

---
### INCOMING WORK ORDER:
Execute the work order staged on disk at:
${TICKET_PATH}

Use view_file or appropriate tools to inspect ${TICKET_PATH}, parse all 4 quarters, implement the code changes, run builds/verifications, generate the walkthrough markdown, and complete the ticket.
---
EOF
)

EXIT_CODE=0
export FORCE_COLOR=1
export PYTHONUNBUFFERED=1
export CLIO_WORKER=1
export CLIO_HEADLESS=1

cd "${WORKSPACE_DIR}"

if [[ -x "${AGY_BIN}" ]]; then
  echo "[INFO] Invoking headless agy with --dangerously-skip-permissions..." | tee -a "${RUN_LOG}"
  "${AGY_BIN}" \
    --dangerously-skip-permissions \
    --mode accept-edits \
    --print-timeout 15m \
    --prompt "${PROMPT_PAYLOAD}" \
    2>&1 | tee -a "${RUN_LOG}" || EXIT_CODE=$?

  if grep -q "print timeout after" "${RUN_LOG}"; then
    echo "[ERROR] agy print timeout triggered before completion!" | tee -a "${RUN_LOG}"
    EXIT_CODE=124
  fi
else
  echo "[ERROR] agy binary not found at ${AGY_BIN}!" | tee -a "${RUN_LOG}"
  EXIT_CODE=127
fi

# Assert Walkthrough Artifact Creation (GitOps Gate)
WALKTHROUGH_FILE="/home/james/stacklabs/walkthroughs/walkthrough_${TICKET_NAME}.md"
if [[ ${EXIT_CODE} -eq 0 ]]; then
  if [[ -f "${WALKTHROUGH_FILE}" ]]; then
    echo "✅ [GITOPS] Walkthrough verified: ${WALKTHROUGH_FILE}" | tee -a "${RUN_LOG}"
  else
    echo "⚠️ [WARN] Walkthrough not found at ${WALKTHROUGH_FILE}, but execution completed." | tee -a "${RUN_LOG}"
  fi
fi

echo "==================================================" | tee -a "${RUN_LOG}"
echo "Execution finished with status code: ${EXIT_CODE}" | tee -a "${RUN_LOG}"
echo "Log stored at: ${RUN_LOG}" | tee -a "${RUN_LOG}"
echo "==================================================" | tee -a "${RUN_LOG}"

# Audio & Desktop Notification dispatch
if [[ -x "${NOTIFY_BIN}" ]]; then
  if [[ ${EXIT_CODE} -eq 0 ]]; then
    "${NOTIFY_BIN}" success "${TICKET_NAME}" "Execution completed successfully with exit code 0." || true
  else
    "${NOTIFY_BIN}" failure "${TICKET_NAME}" "Execution failed with exit code ${EXIT_CODE}. Check log." || true
  fi
fi

exit "${EXIT_CODE}"
