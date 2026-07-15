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
