#!/bin/bash
# Run eye template preview without Qt warnings
export QT_LOGGING_RULES="*=false"
export QT_QPA_PLATFORM_PLUGIN_PATH=""
export QT_X11_NO_MITSHM="1"

cd /home/tolian500/Coding/halloween
python3 eye_template.py
