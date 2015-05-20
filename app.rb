#!/opt/ruby/current/bin/ruby
# -*- coding: utf-8 -*-

require 'rubygems'
require 'sinatra/base'
require 'haml'
require 'csv'
require './lib/storage'
require './lib/paginate'
require 'will_paginate'
require 'will_paginate/active_record'
require 'will_paginate/view_helpers'
require 'will_paginate/view_helpers/sinatra'
require 'yaml'

I18n.enforce_available_locales = false

class SinatraBootstrap < Sinatra::Base
  # require './helpers/render_partial'
  include WillPaginate::Sinatra::Helpers

  enable :sessions

  configfile = '.config.yml'
  if File.exist?(configfile)
  @config = YAML.load_file(configfile)
    username = @config['auth']['username']
    password = @config['auth']['password']

    use Rack::Auth::Basic do |user, pass|
      user == username && pass == password
    end
  end

  helpers do
    def number_with_delimiter(fixnum)
      fixnum.to_s.gsub(/(\d)(?=(\d{3})+(?!\d))/, '\1,')
    end

    def h(text)
      Rack::Utils.escape_html(text)
    end

    def paginate
      will_paginate @contents, :renderer => BootstrapPaginationRenderer
    end
  end

  def initialize(app = nil, params = {})
    super(app)
    @storage = Storage.new
    @root = Sinatra::Application.environment == :production ? '/finance-dashboard/' : '/'
  end

  def logger
    env['app.logger'] || env['rack.logger']
  end

  def open_csv(filename)
    array = []
    open(filename) do |file|
      file.each_line do |line|
        array << line
      end
    end
    return array
  end

  def open_data(filename, &block)
    table = CSV.table(filename, encoding: "UTF-8")
    keys = table.headers

    array = []
    CSV.foreach(File.expand_path(filename), encoding: "UTF-8" ) do |row|
      hashed_row = Hash[*keys.zip(row).flatten]
      pri_key = hashed_row[:date]
      array << hashed_row unless pri_key == "Date"
    end

    return array
  end

  get '/' do
    filename = File.expand_path('public/data/stocks.txt')
    @stocks = open_csv(filename)

    filename = File.expand_path('public/data/summary.csv')
    @summary = open_csv(filename)

    filename = File.expand_path('public/data/summary_15.csv')
    @summary15 = open_csv(filename)

    filename = File.expand_path('public/data/summary_30.csv')
    @summary30 = open_csv(filename)

    session[:recent] = [] unless session[:recent]
    @recent = session[:recent].sort
    haml :index
  end

  get '/stock/:code' do
    filename = 'public/data/ti_' + @params[:code] + '.csv'
    filename = File.expand_path(filename)
    redirect '/' unless File.exist?(filename)

    @data = open_data(filename)
    redirect '/' if @data.length == 0

    @title = "#{@params[:code]} - Finance Dashboard"

    session[:recent] = [] unless session[:recent]
    session[:recent] << @params[:code]
    session[:recent] = session[:recent].last(10).uniq

    @recent = session[:recent].sort
    haml :detail
  end

  run! if app_file == $0
end
