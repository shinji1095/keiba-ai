CREATE TABLE system_metrics (
  id varchar(64) PRIMARY KEY,
  host_id varchar(120) NOT NULL,
  sampled_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL,
  data jsonb NOT NULL
);
CREATE INDEX ix_system_metrics_host_id ON system_metrics(host_id);
CREATE INDEX ix_system_metrics_sampled_at ON system_metrics(sampled_at);
CREATE TABLE system_metric_minutes (
  id varchar(64) PRIMARY KEY,
  host_id varchar(120) NOT NULL,
  sampled_at timestamptz NOT NULL,
  count integer NOT NULL,
  data jsonb NOT NULL
);
CREATE INDEX ix_metric_minute_host_time ON system_metric_minutes(host_id, sampled_at);
CREATE TABLE system_monitoring_alarms (
  id varchar(64) PRIMARY KEY,
  host_id varchar(120) NOT NULL,
  resource varchar(600) NOT NULL,
  level varchar(20) NOT NULL,
  updated_at timestamptz NOT NULL,
  data jsonb NOT NULL
);
CREATE INDEX ix_system_monitoring_alarms_host_id ON system_monitoring_alarms(host_id);
CREATE TABLE system_monitoring_events (
  id varchar(64) PRIMARY KEY,
  host_id varchar(120) NOT NULL,
  resource varchar(600) NOT NULL,
  level varchar(20) NOT NULL,
  message varchar(1000) NOT NULL,
  started_at timestamptz NOT NULL,
  resolved_at timestamptz
);
CREATE INDEX ix_system_monitoring_events_host_id ON system_monitoring_events(host_id);
CREATE INDEX ix_system_monitoring_events_started_at ON system_monitoring_events(started_at);
