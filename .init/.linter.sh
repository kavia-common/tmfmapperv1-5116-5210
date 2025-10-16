#!/bin/bash
cd /home/kavia/workspace/code-generation/tmfmapperv1-5116-5210/FlaskTMFTranslationMiddleware
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

