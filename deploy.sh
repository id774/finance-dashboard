#!/bin/sh

APP_ROOT=/var/www/sinatra/finance-dashboard/
cd $APP_ROOT
git pull
sudo chown -R www-data:www-data $APP_ROOT
sudo chmod -R g+rw,o-rwx $APP_ROOT
sudo service apache2 restart
