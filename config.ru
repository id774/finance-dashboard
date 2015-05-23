require 'rubygems'
require 'sinatra'
require 'logger'
require './lib/applog'
require './app'

Encoding.default_external = 'UTF-8'

logdir = File.dirname(__FILE__) + "/log"
logger = ::Logger.new(logdir + '/app.log')

def logger.write(msg)
  self << msg
end

configure :development do
  require 'sinatra/reloader'
  register Sinatra::Reloader
end

configure :production do
end

set :public_dir, File.dirname(__FILE__) + '/public'
use AppLog, logger
use Rack::CommonLogger, logger

run SinatraBootstrap
