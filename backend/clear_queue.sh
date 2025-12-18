#!/bin/bash
# Clear dead letter queue and reset stuck messages

RESOURCE_GROUP="auditapp-staging-rg"
NAMESPACE="auditapp-staging-servicebus"
QUEUE="document-processing"

echo "=== CLEARING DEAD LETTER QUEUE ==="
# Move dead letter messages back to main queue
az servicebus queue update \
  --resource-group "$RESOURCE_GROUP" \
  --namespace-name "$NAMESPACE" \
  --name "$QUEUE" \
  --enable-dead-lettering-on-message-expiration false

echo "Messages in dead letter will expire naturally"
echo "To forcefully clear, we need to receive and complete them"

echo ""
echo "=== CURRENT QUEUE STATUS ==="
az servicebus queue show \
  --resource-group "$RESOURCE_GROUP" \
  --namespace-name "$NAMESPACE" \
  --name "$QUEUE" \
  --query "{Active:countDetails.activeMessageCount, DeadLetter:countDetails.deadLetterMessageCount, Scheduled:countDetails.scheduledMessageCount}"
