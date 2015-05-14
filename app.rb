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

I18n.enforce_available_locales = false

class SinatraBootstrap < Sinatra::Base
  # require './helpers/render_partial'
  include WillPaginate::Sinatra::Helpers

  helpers do
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
    @root = Sinatra::Application.environment == :production ? '/finance-portal/' : '/'
  end

  def logger
    env['app.logger'] || env['rack.logger']
  end

  def open_summary(filename)
    array = []
    open(filename) do |file|
      file.each_line do |line|
        array << line
      end
    end
    return array
  end

  def open_stock(filename, &block)
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
    filename = File.expand_path('public/data/summary.csv')
    @data = open_summary(filename)
    haml :index
  end

  get '/:code' do
    filename = 'public/data/ti_' + @params[:code] + '.csv'
    filename = File.expand_path(filename)
    @data = open_stock(filename)
    redirect '/' if @data.length == 0
    haml :detail
  end

  run! if app_file == $0
end