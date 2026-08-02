# Art Around Town
A Django project that displays local art events and artists

## Run locally
### Environment setup 
```
# 1. clone and make your way to the root of the project

# 2. active your virtual environment (recommended)
python -m venv venv
. venv/bin/activate

# 3. install dependencies
pip install -r requirements-dev.txt

# 4. environmental variables 
cp .env.example .env
```

### Migrations
```
python3 manage.py makemigrations
python3 manage.py migrate
```

### Fill artists table
To get your relations setup, this guide assumes 
1. You have the original artist csv file imported from Wix somewhere in your
   file system
2. The following env variables are filled in: 
- `BUCKET_NAME` 
- `BUCKET_BASE_PATH`
- `DIGITAL_OCEAN_PERSONAL_ACCESS_TOKEN` 
- `DIGITAL_OCEAN_SECRET_KEY` 
- `DATABASE_URL` 

```
# Parses, cleans, and syncs values in your artist csv file with object and
relational storage
python3 manage.py sync_artists --csvfile <path to csvfile>

# if you'd like to skip object storage upload, add the -s flag or --skip-upload
# python3 manage.py sync_artists --csvfile <path to csvfile> -s
```

### Run the server 
```
python manage.py runserver
```
