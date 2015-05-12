#!/opt/ruby/current/bin/ruby
# -*- coding: utf-8 -*-

class BootstrapPaginationRenderer < WillPaginate::Sinatra::LinkRenderer
  private
  def previous_or_next_page(page, text, classname)
    link(text, page, :class => classname) unless page == false
  end

  public
  def to_html
    html = pagination.map do |item|
      tag(:li,
        ((item.is_a?(Fixnum))?
          page_number(item) :
          send(item)))
    end.map{|x|x.gsub(/><em/, " class=\"active\"><a").gsub(/em/, "a")}.join(@options[:link_separator])

    html = tag(:ul, html)

    @options[:container] ? html_container(html) : html
  end
end
