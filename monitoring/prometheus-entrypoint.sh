#!/bin/sh
sed \
  -e "s|\${GRAFANA_CLOUD_REMOTE_WRITE_URL}|${GRAFANA_CLOUD_REMOTE_WRITE_URL}|g" \
  -e "s|\${GRAFANA_CLOUD_USER}|${GRAFANA_CLOUD_USER}|g" \
  -e "s|\${GRAFANA_CLOUD_TOKEN}|${GRAFANA_CLOUD_TOKEN}|g" \
  /etc/prometheus/prometheus.yml.template > /tmp/prometheus.yml

exec /bin/prometheus \
  --config.file=/tmp/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --storage.tsdb.retention.time=7d
