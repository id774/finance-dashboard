#!/opt/ruby/current/bin/ruby
# -*- coding: utf-8 -*-

require 'rubygems'
require 'sinatra/base'
require 'haml'
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
    @root = Sinatra::Application.environment == :production ? '/sinatra-bootstrap/' : '/'
  end

  def logger
    env['app.logger'] || env['rack.logger']
  end

  get '/' do
    @contents = Content.paginate(:page => params[:page]).order('updated_at desc')
    haml :index
  end

  post '/new' do
    @content = Content.new
    @content.key = params[:key]
    @content.value = params[:value]
    @content.save
    redirect "#{@root}"
  end

  run! if app_file == $0
end
