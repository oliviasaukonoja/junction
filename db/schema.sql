-- MariaDB schema draft for ctsim run history. UNTESTED: not loaded into a MariaDB instance yet.
-- Purpose: make every simulation run reproducible and comparable (scenario + seed + data version -> result),
-- and use spatial types for catchment queries.
-- Requires MariaDB 10.5+ (JSON alias, spatial indexes).

CREATE TABLE data_snapshot (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  taken_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  source        VARCHAR(64) NOT NULL,           -- e.g. 'statfin 11re 2025'
  sha256        CHAR(16) NOT NULL,              -- from scenario.data_fingerprint()
  notes         TEXT
);

CREATE TABLE municipality (
  snapshot_id   INT NOT NULL,
  code          CHAR(3) NOT NULL,
  name          VARCHAR(64) NOT NULL,
  centroid      POINT NOT NULL SRID 0,          -- lon/lat stored as (lon, lat)
  pop_50_74     INT NOT NULL,
  foreign_lang_share DECIMAL(5,4),
  sparse_share  DECIMAL(5,4),
  PRIMARY KEY (snapshot_id, code),
  SPATIAL INDEX (centroid),
  FOREIGN KEY (snapshot_id) REFERENCES data_snapshot(id)
);

CREATE TABLE scenario (
  hash          CHAR(12) PRIMARY KEY,           -- scenario.scenario_hash()
  name          VARCHAR(128) NOT NULL,
  body          JSON NOT NULL
);

CREATE TABLE run (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  scenario_hash CHAR(12) NOT NULL,
  snapshot_id   INT NOT NULL,
  engine_version VARCHAR(16) NOT NULL,
  started_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  seconds       DECIMAL(8,3),
  scans         DOUBLE, additional DOUBLE, km_per_year DOUBLE, working_days DOUBLE,
  cost_total_eur DOUBLE, cost_per_additional_eur DOUBLE,
  result        JSON NOT NULL,                  -- full scenario.run() output
  FOREIGN KEY (scenario_hash) REFERENCES scenario(hash),
  FOREIGN KEY (snapshot_id) REFERENCES data_snapshot(id),
  INDEX (scenario_hash, started_at)
);

CREATE TABLE run_stop (
  run_id        BIGINT NOT NULL,
  seq           SMALLINT NOT NULL,              -- order along the route
  municipality_code CHAR(3) NOT NULL,
  days          DECIMAL(6,2) NOT NULL,
  scans         DOUBLE, additional DOUBLE,
  PRIMARY KEY (run_id, seq),
  FOREIGN KEY (run_id) REFERENCES run(id) ON DELETE CASCADE
);

-- Example: how often did a municipality appear in stored plans across robustness runs?
-- SELECT municipality_code, COUNT(*) / (SELECT COUNT(*) FROM run) AS share_of_runs
-- FROM run_stop GROUP BY municipality_code ORDER BY share_of_runs DESC;
