#!/bin/bash
dnf install -y docker
systemctl enable --now docker
mkdir -p /opt/v2x
cat > /opt/v2x/deploy.sh <<'EOF'
#!/bin/bash
set -euo pipefail
TAG="$1"; REGION=us-east-1
REG=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REG
docker pull $REG/v2x-service:$TAG
docker rm -f v2x-service 2>/dev/null || true
docker run -d --name v2x-service --restart unless-stopped -p 8080:8080 \
  -e AWS_DEFAULT_REGION=$REGION $REG/v2x-service:$TAG
for i in $(seq 1 30); do curl -sf localhost:8080/health && echo && exit 0; sleep 2; done
echo "health check failed"; exit 1
EOF
chmod +x /opt/v2x/deploy.sh
