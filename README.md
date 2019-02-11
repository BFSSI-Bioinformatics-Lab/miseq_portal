# Portal Documentation

### Overview
The MiSeq Portal was built with `Django 2.0.7` and `PostgreSQL 9.5`. 

### Installation/Getting Started Instructions
```bash
# Clone project
git clone https://github.com/bfssi-forest-dussault/miseq_portal.git

# Create new conda environment
conda create -n miseq_portal python=3.6

# Activate the conda environment
source activate miseq_portal

# Install dependencies via pip
pip install -r miseq_portal/local.txt

# Set up PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Check version of PostgresQL. The portal was built on 9.5.14 but it should also work with newer versions
psql -c 'SELECT version();'

# Create user. This user must be the owner of the miseq_portal DB that we'll create in the next command
sudo -u postgres createuser --interactive

# Create fresh DB - it must be named miseq_portal
sudo -u postgres createdb [your username goes here]

# Now that the DB is created, we can populate it with the requisite tables
# This is done with the makemigrations command - note that each app name must be provided 
python miseq_portal/manage.py makemigrations analysis miseq_viewer users core

# Commit the changes to the DB
python miseq_portal/manage.py migrate

# At this point, you should be able to succesfully start the webserver
python miseq_portal/manage.py runserver 0.0.0.0:8000

# You can now access the portal through your web browser via the IP address of the host machine
```

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

**Additional setup to enable JDBC connection with DBeaver:**

1. Change `listen_addresses` from `'local'` to `'*'` in postgresql.conf i.e. `#listen_addresses = '*'  `
2. Under `# IPv4 local connections` in pg_hba.conf change `md5` to `trust` for your host entry (https://stackoverflow.com/questions/15597516/postgres-hba-conf-for-jdbc)
```bash
sudo nano /etc/postgresql/10/main/postgresql.conf  # Make first change here
sudo nano /etc/postgresql/10/main/pg_hba.conf  # Make second change here
sudo service postgresql restart  # Restart service
```

### Administrator Usage
Admins and staff have the ability to upload entire runs to the MiSeq portal database. 
This is done via the miseq_uploader app (_http://192.168.1.61:8000/miseq_uploader/_).

To do this, the user must be logged into the host machine (currently brock@192.168.1.61). 
From here, locally stored runs can be easily uploaded via the 'Upload MiSeq Run' button on the webpage.

The run to be uploaded **must have the same folder structure as a local MiSeq run. 
If the run is only available on BaseSpace, it must be retrieved with [BaseMountRetrieve](https://github.com/BFSSI-Bioinformatics-Lab/BaseMountRetrieve)**.
This structures the run in a format that the portal expects when parsing and uploading run data 
(i.e. reads, InterOp, stats, logs). The user must supply the full path to the run: 
_e.g. /mnt/Dr-Girlfriend/MiSeq/BaseSpace_Projects/Listeria2016WGS/20180813_WGS_M01308_


### Celery + RabbitMQ
Computationally heavy tasks are offloaded to the server via `Celery` and `RabbitMQ`.
Tasks are created with the `@shared_task` decorator and are detected by Celery.
The task queue is managed by the broker, RabbitMQ.

The results for tasks are stored in the backend (rpc? django-db?). TBD.

Celery is distributed with this project, though RabbitMQ must be installed and set up separately.

#### Installing and configuring RabbitMQ
```bash
sudo apt install rabbitmq-server
```

Setting up RabbitMQ with a miseq_portal user can be done with the following commands.
```bash
sudo rabbitmqctl add_user miseq_portal password_goes_here
sudo rabbitmqctl add_vhost miseq_portal_vhost
sudo rabbitmqctl set_user_tags miseq_portal administrator
sudo rabbitmqctl set_permissions -p miseq_portal_vhost miseq_portal ".*" ".*" ".*"
```

RabbitMQ can be monitored via the `RabbitMQ Management` plugin. 
The web interface should be accessible via 0.0.0.0:15672 with the login credentials specified above.
```
sudo rabbitmq-plugins enable rabbitmq_management
```

#### Configuring Celery
A Celery worker must be launched in order to watch for incoming tasks.
Bugs will occur if the concurrency parameter != 1.
```bash
celery -A miseq_portal.taskapp worker -l INFO -E --concurrency 1
```

Celery can be monitored via `flower`. This package is distributed alongside this project.
The following command will launch a web interface that will be accessible via 0.0.0.0:5555.
```bash
celery -A miseq_portal.taskapp flower
```


### Data Backup/Storage
All user supplied Runs are stored on the **BMH-WGS-Backup NAS** (192.168.1.41), 
which is mounted on the host machine (_/mnt/MiSeqPortal_).

This is the **MEDIA_ROOT** as specified in **config.settings.base**:

`MEDIA_ROOT = "/mnt/MiSeqPortal"`

##### Redundant backups
The uploaded runs are also backed up to the **Wolf_Station NAS** (192.168.1.40) into the _BMH-WGS-Backup-MiSeqPortal_ 
shared folder. This is done via the DSM Hyper Backup application and occurs once every week (Sunday evening).

##### Supervisor
The supervisor keeps four processes alive:
1) manage.py runserver
2) celery (assembly queue)
3) celery (analysis queue)
4) flower
 
See the contents of the following config file for details: `/etc/supervisor/conf.d/miseq_portal.conf`. 
Upon making changes to this config file, be sure to run the following command: `sudo supervisorctl reread; and sudo supervisorctl update`

A local web interface for supervisor is available at `0.0.0.0:9001`. 
The configuration for this interface can be found at `/etc/supervisor/supervisord.conf`, 
specifically under the `[inet_http_server]` heading. 
The status of each process, as well as live updating logs can be viewed here.



