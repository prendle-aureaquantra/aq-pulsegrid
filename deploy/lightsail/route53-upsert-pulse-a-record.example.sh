#!/usr/bin/env sh
# Upsert pulse.aureaquantra.com A record -> Lightsail static IP.
# Requires AWS CLI + Route 53 permissions (see iam-policy-route53-pulse-dns.example.json).

set -eu
: "${ROUTE53_HOSTED_ZONE_ID:?Set ROUTE53_HOSTED_ZONE_ID}"
: "${PULSE_DNS_NAME:=pulse.aureaquantra.com.}"
: "${LIGHTSAIL_STATIC_IP:?Set LIGHTSAIL_STATIC_IP}"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

cat >"$TMP" <<EOF
{
  "Comment": "Upsert PulseGrid A record",
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "${PULSE_DNS_NAME}",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{ "Value": "${LIGHTSAIL_STATIC_IP}" }]
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id "${ROUTE53_HOSTED_ZONE_ID}" \
  --change-batch "file://${TMP}"

echo "Submitted. Verify: dig +short ${PULSE_DNS_NAME%.}"
