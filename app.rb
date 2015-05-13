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

  def open_csv(filename, &block)
    array = []
    CSV.foreach(filename) do |row|
      array << [row[0], row[1], row[2], row[3], row[4]] unless row[0] == "Date"
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
    @data = open_csv(filename).reverse
    redirect '/' if @data.length == 0
    haml :detail
  end

  run! if app_file == $0
end
