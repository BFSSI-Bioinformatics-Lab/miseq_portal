"""
Base settings to build other settings files upon.
"""
from pathlib import Path

import environ

ROOT_DIR = environ.Path(__file__) - 3  # (miseq_portal/config/settings/base.py - 3 = miseq_portal/)
APPS_DIR = ROOT_DIR.path('miseq_portal')

env = environ.Env()

READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path('.env')))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool('DJANGO_DEBUG', False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = 'Canada/Eastern'
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres:///miseq_portal'),
}
# https://stackoverflow.com/questions/15790380/django-celery-task-newly-created-model-doesnotexist
DATABASES['default']['ATOMIC_REQUESTS'] = False
DATABASES['default']['NAME'] = 'miseq_portal'
DATABASES['default']['USER'] = 'postgres'
DATABASES['default']['PASSWORD'] = ''
DATABASES['default']['HOST'] = 'localhost'
DATABASES['default']['PORT'] = ''
DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = 'config.urls'
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.humanize', # Handy template tags
    'django.contrib.admin',
]
THIRD_PARTY_APPS = [
    'crispy_forms',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'rest_framework',
    'rest_framework.authtoken',
    'django_celery_results',
    'rest_framework_datatables',
    'widget_tweaks',
    'django_filters',
]
LOCAL_APPS = [
    # Your stuff: custom apps go here
    'miseq_portal.users.apps.UsersAppConfig',
    'miseq_portal.core.apps.CoreConfig',
    'miseq_portal.miseq_viewer.apps.MiseqViewerConfig',
    'miseq_portal.sample_search.apps.SampleSearchConfig',
    'miseq_portal.analysis.apps.AnalysisConfig',
    'miseq_portal.sample_merge.apps.SampleMergeConfig',
    'miseq_portal.miseq_uploader.apps.MiseqUploaderConfig',
    'miseq_portal.sample_workbooks.apps.SampleWorkbooksConfig',
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {
    'sites': 'miseq_portal.contrib.sites.migrations'
}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = 'users.User'
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = 'users:redirect'
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = 'account_login'

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher'
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR('staticfiles'))
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(APPS_DIR.path('static')),
]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
# MEDIA_ROOT = str(APPS_DIR('media'))  # Old default for MEDIA_ROOT
MEDIA_ROOT = "/mnt/MiSeqPortal"  # Store user uploads on BMH-WGS-Backup (~50 TB storage)
if len(list(Path(MEDIA_ROOT).glob("*"))) == 0:
    print("WARNING: There was an issue mounting BMH-WGS-Backup. "
          "Confirm that the NAS has an SFTP connection to the server.")
else:
    print("Confirmed contents of BMH-WGS-Backup")

# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'

# CUSTOM MISEQ WATCHER
# TODO: Implement this as the 'incoming' folder for new MiSeq runs
MISEQ_WATCHER_ROOT = MEDIA_ROOT + 'miseq_watcher'
MISEQ_WATCHER_URL = '/miseq_watcher/'

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        'DIRS': [
            str(APPS_DIR.path('templates')),
        ],
        'OPTIONS': {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            'debug': DEBUG,
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'analysis_extras': 'analysis.templatetags.analysis_extras',
                'miseq_viewer_extras': 'miseq_viewer.templatetags.miseq_viewer_extras',
            }
        },
    },
]
# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (
    str(APPS_DIR.path('fixtures')),
)

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = 'admin/'
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ("""Forest Dussault""", 'forest.dussault@canada.ca'),
]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# django-allauth
# ------------------------------------------------------------------------------
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ALLOW_REGISTRATION = env.bool('DJANGO_ACCOUNT_ALLOW_REGISTRATION', True)
ACCOUNT_AUTHENTICATION_METHOD = 'username'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_ADAPTER = 'miseq_portal.users.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'miseq_portal.users.adapters.SocialAccountAdapter'

# Your stuff...
# ------------------------------------------------------------------------------
APPEND_SLASH = False
MAX_UPLOAD_SIZE = 1719664640  # 2GB
DJANGO_SETTINGS_MODULE = 'miseq_portal.config.settings.local'

# CELERY
INSTALLED_APPS += ['miseq_portal.taskapp.celery.CeleryAppConfig']
if USE_TZ:
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
# CELERY_BROKER_URL = 'amqp://localhost:5672/miseq_portal_vhost'
CELERY_BROKER_URL_CREDENTIALS = env('CELERY_BROKER_URL_CREDENTIALS')
CELERY_BROKER_URL = f'amqp://{CELERY_BROKER_URL_CREDENTIALS}@localhost:5672/miseq_portal_vhost'
# BROKER_URL = 'amqp://guest:guest@localhost:5672/miseq_portal_vhost'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = 'rpc://'
CELERY_RESULT_PERSISTENT = True
# CELERY_RESULT_BACKEND = 'django-db'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ['json']
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = 'json'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = 'json'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-time-limit
CELERYD_TASK_TIME_LIMIT = 5 * 60
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-soft-time-limit
CELERYD_TASK_SOFT_TIME_LIMIT = 60
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-always-eager
CELERY_TASK_ALWAYS_EAGER = False
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True

# Celery tasks were occasionally hanging and the whole server had to be restarted as a result. This fixes(?) that issue.
CELERY_BROKER_POOL_LIMIT = None
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

CELERY_IMPORTS = ('miseq_portal.analysis.tasks',
                  'miseq_portal.sample_merge.tasks')

# Assemblies and regular analysis tasks are split across two separate routes.
# These routes must be specified in the .apply_async() method calls to @shared_task functions.
CELERY_ROUTES = {
    'miseq_portal.analysis.tasks.submit_analysis_job': {'queue': 'analysis_queue'},
    'miseq_portal.analysis.tools.assemble_run.assemble_sample_instance': {'queue': 'assembly_queue'},
}

# REST FRAMEWORK
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_datatables.renderers.DatatablesRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_datatables.filters.DatatablesFilterBackend',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        # https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework_datatables.pagination.DatatablesPageNumberPagination',
    'PAGE_SIZE': 100,
}

# ASSEMBLY PIPELINE SETTINGS
MOB_SUITE_PATH = Path("/home/forest/miniconda3/envs/mob_suite/bin/")
ABRICATE_PATH = Path("/home/forest/miniconda3/envs/abricate/bin/")
STAR_AMR_PATH = Path("/home/forest/miniconda3/envs/staramr/bin/")
CONFINDR_PATH = Path("/home/forest/miniconda3/envs/confindr/bin/")

# Databases
MASH_REFSEQ_DATABASE = Path(MEDIA_ROOT) / 'resources' / 'refseq.genomes.k21s1000.msh'
assert MASH_REFSEQ_DATABASE.exists()

CONFINDR_DB = Path(MEDIA_ROOT) / 'resources' / 'confindr_db'
assert CONFINDR_DB.exists()

CONFINDR_SECRET = Path(MEDIA_ROOT) / 'resources' / 'pubmlst_secret.txt'
assert CONFINDR_SECRET.exists()
