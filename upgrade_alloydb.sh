#!/bin/bash
# upgrade_alloydb.sh - Enable AI integration for existing AlloyDB instance
# Run this from your local machine with gcloud installed.

PROJECT_ID=$(gcloud config get-value project)
REGION=${GOOGLE_CLOUD_REGION:-us-central1}
CLUSTER_NAME=${ALLOYDB_CLUSTER_NAME:-agent-flow-cluster}
INSTANCE_NAME=${ALLOYDB_INSTANCE_NAME:-agent-flow-instance}

echo "🚀 Polishing AlloyDB for Enterprise AI..."

# Enable google_ml_integration flag
# This is required for Vertex AI integration within Postgres
echo "🔧 Enabling google_ml_integration flag on instance $INSTANCE_NAME..."
gcloud alloydb instances update $INSTANCE_NAME \
    --cluster=$CLUSTER_NAME \
    --region=$REGION \
    --database-flags=google_ml_integration=on

echo "✅ AlloyDB flag updated. You may need to restart the instance if prompted."
echo "Next step: Run 'python backend/database/setup_vector.py' to enable extensions."
