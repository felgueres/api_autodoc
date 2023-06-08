#!/bin/bash

# install server deps
sudo apt update
sudo apt install nginx
sudo apt install supervisor
sudo apt install sqlite3

# install python deps 
sudo apt install python3 python3-pip
pip3 install virtualenv
virtualenv venv
source venv/bin/activate
pip3 install -r requirements.txt

# setup server and supervisor
sudo cp upstreamapi.nginx /etc/nginx/sites-enabled/upstreamapi.nginx
sudo unlink /etc/nginx/sites-enabled/default
sudo nginx -s reload 

sudo mkdir /var/log/upstreamapi

sudo touch /etc/supervisor/conf.d/upstreamapi.conf
sudo cp upstreamapi.conf /etc/supervisor/conf.d/upstreamapi.conf
sudo touch /var/log/upstreamapi/upstreamapi.out.log
sudo touch /var/log/upstreamapi/upstreamapi.err.log

# Setup HTTPS
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx

# Observability: follow instructions for grafana + nginx plugin
# Add json format to logs in nginx.conf
# Configure agent to scrape and send logs to /etc/grafana-agent.yaml
# Add geoip2 module to nginx for geoip data
apt-get install nginx-plus-module-geoip2

apt install ffmpeg -y
