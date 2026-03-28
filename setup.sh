#!/usr/bin/env bash
set -e

VENV_DIR="venv"

echo "Creating virtual environment in ./${VENV_DIR}/ ..."
python3 -m venv "${VENV_DIR}"

echo "Installing dependencies from requirements.txt ..."
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel --quiet
"${VENV_DIR}/bin/pip" install -r requirements.txt --quiet
"${VENV_DIR}/bin/pip" install -e . --quiet

echo ""
echo "Setup complete. Activate the virtual environment with:"
echo ""
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "Then run the CLI with:  crew --help"
