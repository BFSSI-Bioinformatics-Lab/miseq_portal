MiSeq-Portal
============

Web portal for managing NGS data


Database
========
**General Postgres setup:**
https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-16-04

**Additional setup to enable JDBC connection with DBeaver:**

1. Change `listen_addresses` from `'local'` to `'*'` in postgresql.conf i.e. `#listen_addresses = '*'  `
2. Under `# IPv4 local connections` in pg_hba.conf change `md5` to `trust` for your host entry (https://stackoverflow.com/questions/15597516/postgres-hba-conf-for-jdbc)
```bash
sudo nano /etc/postgresql/10/main/postgresql.conf  # Make first change here
sudo nano /etc/postgresql/10/main/pg_hba.conf  # Make second change here
sudo service postgresql restart  # Restart service
```

**Using psql:**
```bash
sudo -i -u postgres
psql
\l  # Show all databases
```

**DB name:** miseq_portal

**DB user:** forest
