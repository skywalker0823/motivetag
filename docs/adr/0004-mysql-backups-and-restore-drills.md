# 0004. Daily MySQL dumps to S3 with a weekly automated restore drill

- Status: Accepted
- Date: 2026-09-26

## Context

MySQL runs in a container on the instance's data volume
([0001](0001-single-ec2-with-docker-compose.md)), so there are no RDS automated
backups. The data volume survives an instance rebuild, but not a deleted volume, a
bad migration, an accidental `DELETE`, or a lost availability zone. A backup that
has never been restored is a hope, not a backup.

Targets for a site this size: **RPO ≤ 24 hours**, **RTO under an hour**.

## Decision

- **Backup**: a systemd timer runs `deploy/backup.sh` daily at 03:00 Taipei time.
  It runs `mysqldump --single-transaction` inside the MySQL container (a
  consistent InnoDB snapshot without locking the site; the root password never
  leaves the container), gzips it, checks the dump ends with mysqldump's
  "Dump completed" line, and uploads it with boto3 from the app image.
- **Storage**: a private, encrypted, **versioned** S3 bucket
  (`infra/main/backup.tf`). Dumps expire after 35 days; overwritten versions after
  7. The instance role may put and read objects under `mysql/` but **cannot
  delete**, so a compromised server cannot wipe the history.
- **Restore drill**: every Sunday `deploy/restore_drill.sh` downloads the newest
  dump, loads it into a **throwaway MySQL 8.4 container on tmpfs**, checks there is
  an Alembic version and members, prints row counts next to production's, and
  reports the backup's age (RPO) and the restore time (RTO for the data).
- **Signals**: both jobs publish `BackupSuccess` / `RestoreDrillSuccess` (1 or 0)
  to CloudWatch. Alarms fire when a day passes without a successful backup, or when
  a drill fails ([0006](0006-monitoring-and-alerting.md)).
- The scripts and timers ship in the app image and are installed by each deploy.
- The last three dumps also stay on the server for a quick local restore.

## Consequences

- Worst case we lose up to a day of posts. That is a deliberate trade-off against
  running binlog shipping or a replica.
- The drill proves weekly that the dumps restore on the same MySQL version, and
  gives a measured restore time rather than a guess.
- Dumps are logical: slower to restore than snapshots as data grows, but portable
  (RDS, another region, a laptop).
- The drill uses up to ~768 MB of RAM for a few seconds on a 2 GB host; it runs at
  04:30, the quietest time.

## Alternatives considered

- **EBS snapshots via Data Lifecycle Manager** — crash-consistent, fast to take and
  restore, but restoring means a new volume, and they are harder to test in
  isolation. A good *addition* for faster RTO.
- **Percona XtraBackup / binlog shipping** — point-in-time recovery, far more to run.
- **RDS** — solves this entirely, at the cost [0001](0001-single-ec2-with-docker-compose.md)
  moved away from.
- **S3 Object Lock** — stronger than "no delete permission"; worth it if backups
  ever need to be immutable even to administrators.

## Revisit when

The dump takes minutes, the drill's restore time approaches the RTO, or losing a
day of data becomes unacceptable.
