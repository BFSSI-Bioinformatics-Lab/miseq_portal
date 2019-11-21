
### PostgreSQL
**Basics:**

https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-16-04

**DB name:** miseq_portal

**DB user:** brock

**Using psql:**
```bash
sudo -i -u brock  # Login with user brock
psql  # Launch psql
\l  # Show all databases
\du  # Show all users
```

**Exploring the miseq_portal database:**
```bash
sudo -u brock psql -d miseq_portal  # Login to db
\dt  # Show all tables
select * from miseq_viewer_project;  #  Basic query
```

**Backups**

A cron job has been set to backup the PostgreSQL database periodically.
Use the following command to edit cron jobs:
```crontab -e```

crontab entry to backup the database every day at 1:00AM:
```
0 1 * * * pg_dump miseq_portal > /mnt/Dean-Venture/miseq_portal_postgres_backup/"$(date +"miseq_portal_db_\%Y\%m\%d").bak"
```

Restoring a backup to a brand new database example command:
```
psql miseq_portal_backup_restore < /mnt/Dean-Venture/miseq_portal_postgres_backup/miseq_portal_db_20191121.bak
```

**Additional setup to enable JDBC connection with DBeaver:**

1. Change `listen_addresses` from `'local'` to `'*'` in postgresql.conf i.e. `#listen_addresses = '*'  `
2. Under `# IPv4 local connections` in pg_hba.conf change `md5` to `trust` for your host entry (https://stackoverflow.com/questions/15597516/postgres-hba-conf-for-jdbc)
```bash
sudo nano /etc/postgresql/10/main/postgresql.conf  # Make first change here
sudo nano /etc/postgresql/10/main/pg_hba.conf  # Make second change here
sudo service postgresql restart  # Restart service
```
