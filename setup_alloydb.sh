#!/bin/bash
# setup_alloydb.sh - Automates the creation of an AlloyDB cluster and instance

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
NETWORK="default"
CLUSTER_ID="my-alloydb-cluster"
INSTANCE_ID="my-primary-instance"
DB_PASSWORD="SuperSecretPassword123!" # Change this!

echo "🚀 Setting up AlloyDB in project: $PROJECT_ID ($REGION)"

echo "1. Enabling required APIs..."
gcloud services enable \
    alloydb.googleapis.com \
    servicenetworking.googleapis.com \
    compute.googleapis.com \
    --project=$PROJECT_ID

echo "2. Setting up VPC Private Services Access on network: $NETWORK"
# Check if the IP range already exists to avoid errors
if ! gcloud compute addresses describe google-managed-services-$NETWORK --global --project=$PROJECT_ID > /dev/null 2>&1; then
    echo "Allocating IP range..."
    gcloud compute addresses create google-managed-services-$NETWORK \
        --global \
        --purpose=VPC_PEERING \
        --prefix-length=16 \
        --description="peering range for Google services" \
        --network=$NETWORK \
        --project=$PROJECT_ID
else
    echo "IP range google-managed-services-$NETWORK already exists. Skipping."
fi

# Check if the peering connection already exists
if ! gcloud services vpc-peerings list --network=$NETWORK --project=$PROJECT_ID | grep -q "servicenetworking-googleapis-com"; then
    echo "Creating VPC peering connection..."
    gcloud services vpc-peerings connect \
        --service=servicenetworking.googleapis.com \
        --ranges=google-managed-services-$NETWORK \
        --network=$NETWORK \
        --project=$PROJECT_ID
else
    echo "VPC peering already exists. Skipping."
fi

echo "3. Creating AlloyDB Cluster ($CLUSTER_ID)..."
# This can take 10-15 minutes
if ! gcloud alloydb clusters describe $CLUSTER_ID --region=$REGION --project=$PROJECT_ID > /dev/null 2>&1; then
    gcloud alloydb clusters create $CLUSTER_ID \
        --password="$DB_PASSWORD" \
        --network=$NETWORK \
        --region=$REGION \
        --project=$PROJECT_ID
else
    echo "Cluster $CLUSTER_ID already exists. Skipping."
fi

echo "4. Creating AlloyDB Primary Instance ($INSTANCE_ID)..."
# This can take another 10-15 minutes
if ! gcloud alloydb instances describe $INSTANCE_ID --cluster=$CLUSTER_ID --region=$REGION --project=$PROJECT_ID > /dev/null 2>&1; then
    gcloud alloydb instances create $INSTANCE_ID \
        --cluster=$CLUSTER_ID \
        --region=$REGION \
        --instance-type=PRIMARY \
        --cpu-count=2 \
        --project=$PROJECT_ID
else
    echo "Instance $INSTANCE_ID already exists. Skipping."
fi

echo "✅ AlloyDB Setup Complete!"
echo ""
echo "Your connection string for the backend .env or Cloud Run is:"
echo "ALLOYDB_INSTANCE=\"projects/$PROJECT_ID/locations/$REGION/clusters/$CLUSTER_ID/instances/$INSTANCE_ID\""
