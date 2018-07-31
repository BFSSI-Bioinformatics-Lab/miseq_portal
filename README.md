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

**DB name:** bfssi_portal

**DB user:** forest


Basic Commands
--------------

Setting Up Your Users
^^^^^^^^^^^^^^^^^^^^^

* To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

* To create an **superuser account**, use this command::

    $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

Test coverage
^^^^^^^^^^^^^

To run the tests, check your test coverage, and generate an HTML coverage report::

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

Running tests with py.test
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  $ pytest

