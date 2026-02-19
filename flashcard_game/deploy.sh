#!/bin/bash
set -e

VM_HOST="ferret-whale.exe.xyz"
REMOTE_DIR="~/www"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Deploying flashcard app to $VM_HOST..."

# Transfer src contents to remote ~/www/
echo "Transferring files..."
rsync -avz "$SCRIPT_DIR/src/" "$VM_HOST:$REMOTE_DIR/"

# Transfer Dockerfile
scp "$SCRIPT_DIR/static.Dockerfile" "$VM_HOST:$REMOTE_DIR/"

# Build and run on VM
echo "Building and starting container..."
ssh "$VM_HOST" "cd $REMOTE_DIR && \
    docker build -f static.Dockerfile -t flashcard-app:latest . && \
    docker rm -f flashcard-app 2>/dev/null || true && \
    docker run -d --name flashcard-app --restart unless-stopped -p 80:8000 flashcard-app:latest"

# Get public IP and verify
echo "Verifying deployment..."
PUBLIC_IP=$(ssh "$VM_HOST" "curl -s ifconfig.me")
ssh "$VM_HOST" "docker ps --filter name=flashcard-app --format 'Container: {{.Names}} Status: {{.Status}}'"

echo ""
echo "Deployed successfully!"
echo "  Homepage:        http://$PUBLIC_IP/"
echo "  Flashcards Game: http://$PUBLIC_IP/flashcards.html"
