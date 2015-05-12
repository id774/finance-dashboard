#!/opt/ruby/current/bin/ruby
# -*- coding: utf-8 -*-

require 'active_record'
require 'will_paginate'
require 'will_paginate/active_record'

class Content < ActiveRecord::Base
  self.per_page = 5
end

class Storage
  def initialize
    prepare_database
  end

  def create
    create_table unless model_class.table_exists?
  end

  def drop
    drop_table if model_class.table_exists?
  end

  private

  def prepare_database
    ActiveRecord::Base.configurations = YAML.load_file(File.expand_path(File.join(File.dirname(__FILE__),
      '..', 'config', 'database.yml')))
    ActiveRecord::Base.establish_connection(:development)
    create_table unless model_class.table_exists?
  end

  def model_class
    Content
  end

  def column_definition
    {
      :key => :string,
      :value => :string,
      :created_at => :datetime,
      :updated_at => :datetime
    }
  end

  def unique_key
    :id
  end

  def create_table
    ActiveRecord::Migration.create_table(model_class.table_name){|t|
      column_definition.each_pair {|column_name, column_type|
        t.column column_name, column_type
      }
    }
  end

  def drop_table
    ActiveRecord::Migration.drop_table(model_class.table_name)
  end
end
