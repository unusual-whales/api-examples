#!/usr/bin/env bash

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_PROTO_DIR="$SCRIPT_DIR/protos/client"
OUTPUT_DIR="$SCRIPT_DIR/protos_gen/client"

# Confirm we are working in a virtual environment that will not pollute global packages
if [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: Virtual environment not detected. Please run 'source .venv/bin/activate' first."
    exit 1
fi

cd "$SCRIPT_DIR"

mkdir -p "$OUTPUT_DIR"
touch "$SCRIPT_DIR/protos_gen/__init__.py"
touch "$OUTPUT_DIR/__init__.py"

echo "Generating client protobuf files..."

# Generate Python pb2 files from .proto sources
for proto_file in "$CLIENT_PROTO_DIR"/*.proto; do
  if [ -f "$proto_file" ]; then
    python -m grpc_tools.protoc \
    --proto_path="$CLIENT_PROTO_DIR" \
    --python_out="$OUTPUT_DIR" \
    "$proto_file"
  fi
done

# Fix imports to be relative
find "$OUTPUT_DIR" -name "*_pb2.py" -type f -exec sed -i 's/^import \([a-z_-]*\)_pb2/from . import \1_pb2/' {} \;

echo "Done! Generated files in $OUTPUT_DIR"
