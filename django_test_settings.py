import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


INSTALLED_APPS = (
    'tests',
)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    },
}
SECRET_KEY = 'dummy'
