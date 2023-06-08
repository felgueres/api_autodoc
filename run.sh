!#/bin/bash

gunicorn -w 3 serve:app